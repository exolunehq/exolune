"""Contrôles CPU ciblés du format et des raccords ; aucun banc ni rendu GPU."""
import copy
import unittest
from unittest.mock import patch

import numpy as np
import parcours as cine


class Splines(unittest.TestCase):
    def test_c2_aux_noeuds_et_arrets(self):
        t = np.array([0., .2, 1., 1.5, 3.])
        p = np.array([[0,0], [1,2], [2,1], [4,1], [5,-1]])
        s = cine.Spline(t,p,[0,2,4])
        np.testing.assert_allclose(s(t),p,atol=1e-12)
        for derivative in (0,1,2):
            np.testing.assert_allclose(s(t[1:-1]-1e-9,derivative),s(t[1:-1]+1e-9,derivative),atol=2e-5)
        np.testing.assert_allclose(s(t[[0,2,4]],1),0,atol=1e-12)
        np.testing.assert_allclose(s(t[[0,2,4]],2),0,atol=1e-12)

    def test_pas_de_retour_a_l_arret(self):
        s = cine.Spline(np.arange(6.),[0,1,1.01,1.010001,1.010002,2],[0,3,5])
        self.assertGreaterEqual(np.diff(s(np.linspace(0,5,10001))[:,0]).min(),-1e-12)

    def test_coordonnees_et_dateline(self):
        np.testing.assert_allclose(cine.direction([[0,0],[90,0],[0,90]]),np.eye(3),atol=1e-12)
        p = cine.unit(np.array([cine.direction([0,179]),cine.direction([0,-179])]).mean(axis=0))
        self.assertAlmostEqual(abs(cine.latlon(p)[1]),180)


class Horloge(unittest.TestCase):
    def flight(self, kinds, positions, stops=()):
        times = np.arange(len(positions))*4.
        curve = cine.Spline(times,np.c_[positions,np.zeros((len(positions),2))],stops)
        ranges = [(int(a*60),int(b*60),{'type':k}) for a,b,k in zip(times[:-1],times[1:],kinds)]
        return cine.FlightPath(np.linspace(0,times[-1],2401),
            lambda t: tuple(curve(t,d) for d in (0,1,2)),ranges,60)

    def test_vol_c2_croisiere_et_pointes_bornees(self):
        flight = self.flight(['approche','rase-mottes','mer'],[0,400,1200,1600])
        for join in (4.,8.):
            before = flight(np.array([join-1e-7]))
            after = flight(np.array([join+1e-7]))
            for a,b in zip(before,after):
                np.testing.assert_allclose(a,b,atol=1e-4)
            self.assertGreater(np.linalg.norm(before[1]),1)
        for a in (0,4,8):
            t = np.linspace(a,a+4,1001)
            speed = np.linalg.norm(flight(t)[1],axis=1)
            self.assertGreater(speed.min(),0)
            self.assertLessEqual(speed.max(),1.5*speed.mean())
            cruise = np.linalg.norm(flight(np.linspace(a+1,a+3,101))[1],axis=1)
            self.assertLess(np.ptp(cruise),1e-7)

    def test_seuls_les_arrets_demandes(self):
        flight = self.flight(['approche','atterrissage','pause','decollage','mer'],
                             [0,400,600,600,900,1300],[2,3])
        for t in (8.,9.,11.,12.):
            pos,vel,acc = flight(np.array([t]))
            np.testing.assert_allclose(pos,[[600,0,0]],atol=1e-9)
            np.testing.assert_allclose(vel,0,atol=1e-9)
            np.testing.assert_allclose(acc,0,atol=1e-9)
        for t in (0.,4.,16.,20.):
            self.assertGreater(np.linalg.norm(flight(np.array([t]))[1]),0)

    def test_raccord_orbite_c2_et_horloge_conservee(self):
        def evaluate(t):
            e = np.exp(-t/4)
            return (np.c_[100*t,1000*e,np.zeros(len(t))],
                    np.c_[np.full(len(t),100),-250*e,np.zeros(len(t))],
                    np.c_[np.zeros(len(t)),62.5*e,np.zeros(len(t))])
        flight = cine.FlightPath(np.linspace(0,8,1601),evaluate,
            [(0,240,{'type':'orbite'}),(240,480,{'type':'approche'})],60)
        t = np.linspace(0,4,101)
        for actual,expected in zip(flight(t),evaluate(t)):
            np.testing.assert_allclose(actual,expected,atol=1e-9)
        for before,after in zip(flight(np.array([4-1e-7])),flight(np.array([4+1e-7]))):
            np.testing.assert_allclose(before,after,atol=1e-4)


class Scenarios(unittest.TestCase):
    def setUp(self):
        # Relief plat uniquement dans ces tests isolés ; generate appelle bien cp.elevation.
        self.mock = patch.object(cine.cp,"elevation",side_effect=lambda ctx,p: np.zeros(len(p)))
        self.mock.start(); self.addCleanup(self.mock.stop)
        self.scenario = {"fps":60,"graine":0,"depart":[0,0,2000],"meteo":30,
                         "segments":[{"type":"orbite","duree":1,"point":[0,.001],"hauteur":150},
                                     {"type":"atterrissage","duree":1,"point":[0,.002],"hauteur":4},
                                     {"type":"pause","duree":1},
                                     {"type":"decollage","duree":1,"hauteur":150},
                                     {"type":"rase-mottes","duree":1,"points":[[.001,.003],[.002,.004]],"hauteur":150},
                                     {"type":"mer","duree":1,"point":[.002,.005],"hauteur":20}]}

    def test_types_temps_gardes_pause(self):
        fps,views,nav,cam,fov,weather,summary = cine.generate(self.scenario)
        self.assertEqual(len(nav),360)
        self.assertTrue(np.isfinite(nav).all() and np.isfinite(cam).all())
        np.testing.assert_allclose(weather,30+np.arange(360)/60)
        np.testing.assert_allclose(nav[120:180],np.tile(nav[120],(60,1)),atol=1e-8)
        self.assertAlmostEqual(nav[120,2],4,places=7)
        self.assertTrue((views=="exterieur").all())
        self.assertGreaterEqual(summary["segments"][4]["garde_min_m"],150-1e-5)
        self.assertLess(summary["segments"][1]["vitesse_min_m_s"],1e-6)

    def test_exterieur_fondu_et_cockpit(self):
        s = copy.deepcopy(self.scenario)
        s["segments"][1]["camera"] = {"type":"libre","distance":40,"cap_relatif":70,"fondu":.5,"fov":75}
        s["segments"][2]["camera"] = "cockpit"
        _,views,nav,cam,fov,_,_ = cine.generate(s)
        self.assertTrue((views[120:180]=="cockpit").all())
        self.assertEqual(fov[60],60)  # début du fondu, aucun saut de FOV
        self.assertEqual(fov[119],75)
        xyz = cine.direction(cam[:,:2])*(cine.cp.R+cam[:,2:3])
        self.assertLess(np.linalg.norm(xyz[60]-xyz[59]),5)

    def test_regard_paysage_oppose(self):
        s = copy.deepcopy(self.scenario)
        s["segments"][0]["camera"] = {"type":"libre","regard":"paysage","cap":0}
        s["segments"][1]["camera"] = {"type":"libre","regard":"paysage","cap":180,"fondu":.5}
        _,_,_,cam,_,_,_ = cine.generate(s)
        self.assertTrue(np.isfinite(cam).all())

    def test_pause_apres_correction_de_garde(self):
        s = copy.deepcopy(self.scenario)
        s["depart"][2] = 2
        s["segments"] = [{"type":"pause","duree":1},{"type":"decollage","duree":1,"hauteur":150}]
        _,_,nav,_,_,_,_ = cine.generate(s)
        np.testing.assert_allclose(nav[:60],np.tile(nav[0],(60,1)),atol=1e-8)

    def test_erreurs_de_scenario(self):
        for key,value in [("fps",0),("graine",42)]:
            s = copy.deepcopy(self.scenario); s[key] = value
            with self.assertRaises(ValueError): cine.generate(s)
        s = copy.deepcopy(self.scenario); s["segments"][0]["duree"] = .012
        with self.assertRaises(ValueError): cine.generate(s)

    def test_segment_mer_refuse_la_terre(self):
        s = copy.deepcopy(self.scenario); s["segments"] = [{"type":"mer","duree":1,"point":[0,.001]}]
        with patch.object(cine.cp,"elevation",side_effect=lambda ctx,p: np.full(len(p),40)):
            with self.assertRaisesRegex(ValueError,"émergé"): cine.generate(s)

    def test_mer_basse_ignore_marge_terrain(self):
        for height in (3,5):
            with self.subTest(hauteur=height):
                s = {'fps':60,'depart':[0,0,height],'marge':30,'segments':[
                    {'type':'mer','duree':2,'point':[0,.002],'hauteur':height},
                    {'type':'mer','duree':2,'point':[0,.005],'hauteur':height}]}
                _,_,nav,_,_,_,summary = cine.generate(s)
                np.testing.assert_allclose(nav[:,2],height,atol=1e-6)
                for seg in summary['segments']:
                    self.assertAlmostEqual(seg['garde_min_m'],height,places=5)
                    self.assertGreater(seg['vitesse_min_m_s'],0)
                    self.assertLess(seg['vitesse_max_m_s'],1.5*seg['vitesse_moy_m_s'])

    def test_marge_locale_et_rase_mottes(self):
        s = {'fps':60,'depart':[0,0,5],'marge':12,'segments':[
            {'type':'rase-mottes','duree':2,'point':[0,.002],'hauteur':5,'marge':18},
            {'type':'rase-mottes','duree':2,'point':[0,.004],'hauteur':5,'marge':7}]}
        _,_,_,_,_,_,summary = cine.generate(s)
        self.assertGreaterEqual(summary['segments'][0]['garde_min_m'],18)
        self.assertGreaterEqual(summary['segments'][1]['garde_min_m'],7)
        self.assertLess(summary['segments'][1]['garde_min_m'],12)
        s['segments'][0]['marge'] = 0
        with self.assertRaisesRegex(ValueError,'marge'): cine.generate(s)

    def test_mer_sous_trois_metres_refusee(self):
        s = {'depart':[0,0,5],'segments':[{'type':'mer','duree':1,'point':[0,.001],'hauteur':2.9}]}
        with self.assertRaisesRegex(ValueError,'3 m'): cine.generate(s)

    def test_pause_seule(self):
        s = {'depart':[0,0,4],'segments':[{'type':'pause','duree':1}]}
        _,_,nav,_,_,_,summary = cine.generate(s)
        np.testing.assert_allclose(nav,np.tile(nav[0],(60,1)),atol=1e-8)
        self.assertEqual(summary['segments'][0]['vitesse_max_m_s'],0)

    def test_orbite_altitude_exponentielle(self):
        s = {'depart':[0,0,2000],'segments':[
            {'type':'orbite','duree':4,'point':[0,.003],'altitude':150},
            {'type':'approche','duree':4,'point':[0,.006],'hauteur':30}]}
        _,_,nav,_,_,_,summary = cine.generate(s)
        u = np.arange(0,240,15)/240
        expected = np.exp((1-u)*np.log(3000)+u*np.log(1150))-1000
        np.testing.assert_allclose(nav[:240:15,2],expected,atol=1e-7)
        for seg in summary['segments']:
            self.assertGreater(seg['vitesse_min_m_s'],0)


if __name__ == "__main__":
    unittest.main()
