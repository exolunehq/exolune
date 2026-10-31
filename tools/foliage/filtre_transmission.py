"""Filtre les niveaux d'une hiérarchie par transmission isotrope."""
import struct
import numpy as np


def filter_volume(src, dest):
    with src.open('rb') as f, dest.open('wb') as out:
        header=f.read(40); out.write(header)
        magic,n,levels,*bounds=struct.unpack('<8s2I6f',header)
        if magic!=b'FOLVOL01' or levels!=n.bit_length():
            raise ValueError('Entête de volume invalide')
        lo=np.array(bounds[:3]); hi=np.array(bounds[3:])
        size=n
        current=np.frombuffer(f.read(size**3*32),dtype='<f4').reshape(size,size,size,8).copy()
        out.write(current.astype('<f4').tobytes())
        while size>1:
            childstep=(hi-lo)/size
            meanface=(childstep[0]*childstep[1]+childstep[1]*childstep[2]+childstep[0]*childstep[2])/3
            vol=np.prod(childstep)
            sigma=-np.log1p(-np.minimum(current[...,0].astype(np.float64),1-1e-12))*meanface/vol
            half=size//2
            block=sigma.reshape(half,2,half,2,half,2)
            axis_sigmas=[]
            # Array axes Z,Y,X correspond to position axes 2,1,0.
            for subaxis,dist,remaining in [(5,childstep[0],(1,3)),(3,childstep[1],(1,4)),(1,childstep[2],(2,4))]:
                # Two child transmittances in each of four columns; then average columns.
                transmission=np.exp(-block.sum(axis=subaxis)*dist).mean(axis=remaining)
                axis_sigmas.append(-np.log(np.maximum(transmission,1e-300))/(2*dist))
            sigma_parent=sum(axis_sigmas)/3
            parent_step=childstep*2
            parent_meanface=(parent_step[0]*parent_step[1]+parent_step[1]*parent_step[2]+parent_step[0]*parent_step[2])/3
            parent_vol=np.prod(parent_step)
            old=np.frombuffer(f.read(half**3*32),dtype='<f4').reshape(half,half,half,8).copy()
            old[...,0]=1-np.exp(-sigma_parent*parent_vol/parent_meanface)
            out.write(old.astype('<f4').tobytes())
            current=old; size=half
    return dest
