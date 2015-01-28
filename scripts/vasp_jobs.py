"""
This script demonstrates the usage of the modules mpinterfaces/calibrate.py
and mpinterfaces/measurement.py to setup and run vasp jobs
Note: use your own materials project key to download the required structure
"""

import os
import sys
import shutil as shu
import subprocess as sp
import socket
from math import sqrt
from collections import OrderedDict
import numpy as np

from pymatgen.matproj.rest import MPRester
from pymatgen.io.vaspio.vasp_input import Incar, Poscar, Potcar, Kpoints
from pymatgen.core.structure import Structure
from pymatgen.core.lattice import Lattice
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from fireworks.user_objects.queue_adapters.common_adapter import CommonAdapter

from mpinterfaces import *

#---------------------------------------------
# STRUCTURE
#---------------------------------------------        
#get structure from materialsproject, use your own key       
strt = get_struct_from_mp('Pt', MAPI_KEY="dwvz2XCFUEI9fJiR")
#convert from fcc primitive to conventional cell
#the conventional unit cell is used to create the slab
#this is important becasue the hkl specification for the required slab
#is wrt the provided unit cell
sa = SpacegroupAnalyzer(strt)
structure_conventional = sa.get_conventional_standard_structure()
strt = structure_conventional.copy()
#create slab
iface = Interface(strt, hkl=[1,1,1], min_thick=10, min_vac=10,
                  supercell=[1,1,1])

#---------------------------------------------
# VASP INPUT FILES
#---------------------------------------------                
incar_dict = {
                 'SYSTEM': 'Pt slab', 
                 'ENCUT': 500, 
                 'ISIF': 2, 
                 'IBRION': 2, 
                 'ISMEAR': 1, 
                 'EDIFF': 1e-06, 
                 'EDIFFG': -0.01, 
                 'NPAR': 8, 
                 'SIGMA': 0.1, 
                 'PREC': 'Accurate'
    }
incar = Incar.from_dict(incar_dict)
poscar = Poscar(iface)#, selective_dynamics = np.ones(iface.frac_coords.shape))
potcar = Potcar(poscar.site_symbols)
kpoints = Kpoints.automatic(20)#(80)

#---------------------------------------------
# JOB DEFINITIONS
#---------------------------------------------        
#set job list
encut_list = [] #range(400,800,100)
turn_knobs = OrderedDict(
    [
        ('ENCUT', encut_list)
    ])
#directory in which the jobs will be setup and run
job_dir = 'test'

#---------------------------------------------
# COMPUTATIONAL RESOURCE SETTINGS
#---------------------------------------------
qadapter = None
job_cmd = None
nprocs = 16
nnodes = 1
walltime = '24:00:00'
incar['NPAR'] = int(sqrt(nprocs))
d = {}
wait = True
#hipergator
if 'gator' in socket.gethostname():
    d = {'type':'PBS',
     'params':
     {
         'nnodes': str(nnodes),
         'ppnode': str(int(nprocs/nnodes)),
         'walltime': walltime,
         'job_name': 'vasp_job',
         'pre_rocket': '#PBS -l pmem=1000mb',
         'rocket_launch': 'mpirun /home/km468/Software/VASP/vasp.5.3.5/vasp'
     }
    }
#stampede
elif 'stampede' in socket.gethostname():
    d = {'type':'SLURM',
     'params':
     {
         'nodes': str(nnodes),
         'ntasks': str(nprocs),
         'walltime': walltime,
         'queue':'normal',
         'account':'TG-DMR050028N',
         'job_name': 'vasp_job',
         'rocket_launch': 'ibrun /home1/01682/km468/Software/VASP/vasp.5.3.5/vasp'
     }
    }
#henniggroup machines    
elif socket.gethostname() in ['hydrogen', 'helium', 'lithium', 'beryllium', 'carbon']:    
    job_cmd = ['nohup',
               '/opt/openmpi_intel/bin/mpirun',
               '-n', str(nprocs),
               '/home/km468/Software/VASP/vasp.5.3.5/vasp']
    wait = False    
else:
    job_cmd = ['ls', '-lt']
    wait = False
    
if d:    
    qadapter = CommonAdapter(d['type'], **d['params'])

#---------------------------------------------
# SETUP JOBS
#---------------------------------------------        
cal = CalibrateSlab(incar, poscar, potcar, kpoints, 
                    turn_knobs=turn_knobs, qadapter=qadapter,
                    job_cmd = job_cmd, job_dir=job_dir, wait=wait )
#list of calibrate objects
cal_objs = [cal]
#check whether the cal jobs were done 
Calibrate.check_calcs(cal_objs)
#set the measurement
measure = Measurement(cal_objs, job_dir='./Measurements')
#set the measurement jobs
for cal in cal_objs:                    
    measure.setup_static_job(cal)
    #measure.setup_solvation_job(cal)
    
#---------------------------------------------
# RUN
#---------------------------------------------
#will run calibration jobs if the job is not done and is dead
measure.run()

