from __future__ import division, unicode_literals, print_function

"""
Create a workflow and submit it to the 'fireworks' database on hydrogen

Note 1:
      the database for job submission('fireworks') is
      on the mongodb server running on hydrogen.
      use own account to run the script.
      contact me(km468@cornell.edu) to create a database account
      
Note 2:
        Since hydrogen is part of the hermes subnetwork, direct connection to the database
        is not possible. So tunell port number 27017 from your local machine to port 27017
        on hydrogen via ssh:
        ssh -N -f -L 27017:10.1.255.101:27017 username@hermes.mse.ufl.edu
        if port 27017 on the machine that you are running is not available,
        use another port number for tunneling. example:-
        ssh -N -f -L 27030:10.1.255.101:27017 username@hermes.mse.ufl.edu
        mind: if the tunneled port is changed, the port number in the
        launchpad initialization should also be changed
"""

import numpy as np

from pymatgen import Lattice
from pymatgen.core.structure import Structure
from pymatgen.io.vaspio.vasp_input import Incar, Poscar, Potcar, Kpoints

from fireworks import Firework, Workflow, LaunchPad
from fireworks.core.rocket_launcher import launch_rocket #rapidfire

from mpinterfaces.firetasks import MPINTCalibrateTask, MPINTMeasurementTask


#---------------------------------
# INITIAL INPUTSET
#---------------------------------
#structure
system = 'Pt bulk'
atoms = ['Pt']
    
a0 = 3.965
lvec = [ [0.5, 0.0, 0.5], [0.5, 0.5, 0.0], [0.0, 0.5, 0.5] ]
lvec = np.array(lvec) * a0
lattice = Lattice(lvec)
structure = Structure( lattice,
                        atoms,
                        [ [0.0, 0.0, 0.0] ],
                        coords_are_cartesian=False)

incarparams = {'System':'test',
                   'ENCUT': 400,
                   'ISMEAR': 1,
                   'SIGMA': 0.1,
                   'EDIFF':1E-6}
incar = Incar(params=incarparams)
poscar = Poscar(structure, comment=system, selective_dynamics=None)
potcar = Potcar(symbols = poscar.site_symbols, functional='PBE',
                sym_potcar_map=None)
kpoints = Kpoints(kpts=((8, 8, 8),))

#-------------------------------------------------
# FIRETASK
#
# calibratebulk task
#------------------------------------------------
calparams1 = {}
calparams1['incar'] = incar.as_dict()
calparams1['poscar'] = poscar.as_dict()
calparams1['kpoints'] = kpoints.as_dict()
calparams1['que'] = {}
#submit script setting for hipergator
#calparams1['que'] = {
#                     'type':'PBS',
#                     'params':
#                     {
#                     'nnodes': '1',
#                     'ppnode': '8',
#                     'walltime': '24:00:00',
#                     'job_name': 'test_job',
#                     'rocket_launch': 'mpirun ~/Software/vasp.5.3.5/vasp'
#                     }
#                     }
#if running on henniggroup machines set the job_cmd
#job_cmd = ['nohup',
#           '/opt/openmpi_intel/bin/mpirun',
#           '-n','16',
#           '/home/km468/Software/VASP/vasp.5.3.5/vasp']

turn_knobs = { 'ENCUT' : range(400, 900, 100),
               'KPOINTS': [k for k in range(20, 40, 10)]
             }
#type of calibration to be done: basically the name of calibrate calss to
#be used. available options: CalibrateMolecule, CalibrateSlab, CalibrateBulk
calparams1['calibrate'] = 'CalibrateBulk'
calparams1['turn_knobs'] = turn_knobs
#calparams1['job_cmd'] = job_cmd
#specify other parmaters to the constructor here
calparams1['other_params'] = { 'job_dir':'calBulk'}

caltask1 = MPINTCalibrateTask(calparams1)

#---------------------------------------------------
# FIRETASK
#
# calibrateslab task
#---------------------------------------------------
calparams2 = {}
calparams2 = {k:calparams1[k] for k in calparams1.keys()}
calparams2['calibrate'] = 'CalibrateSlab'
calparams2['system'] = {'hkl':[1,1,1], 'ligand':None}
calparams2['other_params'] = {'job_dir':'calSlab'}

caltask2 = MPINTCalibrateTask(calparams2)

#---------------------------------------------------
# FIRETASK
#
# Measurement task
#---------------------------------------------------
msrparams1 = {}
msrparams1['measurement'] = 'MeasurementSlab'
msrparams1['que'] = calparams1['que']
msrparams1['other_params'] = {'job_dir':'Measurement_1'}
msrtask1 = MPINTMeasurementTask(msrparams1)

#--------------------------------------------------
# FIREWORKS
#
# create the fireworks from the firetasks 
#--------------------------------------------------
fw_calibrate = Firework([caltask1, caltask2], name="fw_calibrate")
fw_measure = Firework([msrtask1], name="fw_measurement", parents=[fw_calibrate])

#-----------------------------------------------------
# WORKFLOW
#
#create workflow from the fireworks
#-----------------------------------------------------
wf = Workflow([fw_calibrate, fw_measure], name="MPINT_workflow")

#---------------------------------------------------------------------
# connect to the fireworks database and add workflow to it
# use your own account
#--------------------------------------------------------------------
launchpad = LaunchPad(host='localhost', port=27017, name='fireworks',
                       username="km468", password="km468")
print('fireworks in the database before adding the workflow: \n',
      launchpad.get_fw_ids())
launchpad.add_wf(wf)
print('fireworks in the database: \n', launchpad.get_fw_ids())



##ignore, for testing purposes only
#fw1 = Firework([caltask1], name="calibrate")
#fw3 = Firework(pptask, name="post_process", parents=[fw1, fw2])
#wf = Workflow([fw1], name="mpint workflow")
#wf = Workflow([fw1, fw2, fw3], name="mpint workflow")