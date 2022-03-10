# Imports
import os
from robosample import *

# Load Amber files
prmtop = AmberPrmtopFile("ala10/ligand.prmtop")
inpcrd = AmberInpcrdFile("ala10/ligand.rst7")

# Hardware platform
platform = Platform.getPlatformByName('GPU')
properties={'nofThreads': 0}

# Create a Robosample system by calling createSystem on prmtop
if os.path.exists("robots"):
  shutil.rmtree("robots")

system = prmtop.createSystem(createDirs = True,
	nonbondedMethod = "CutoffPeriodic",
 	nonbondedCutoff = 1.44*nanometer,
 	constraints = None,
 	rigidWater = True,
 	implicitSolvent = True,
 	soluteDielectric = 1.0,
 	solventDielectric = 78.5,
 	removeCMMotion = False
)

integrator = HMCIntegrator(300*kelvin,   # Temperature of head bath
                           0.001*picoseconds) # Time step

# Create Simulation object
simulation = Simulation(prmtop.topology, system, integrator, platform, properties)
simulation.reporters.append(PDBReporter('temp', 1))
simulation.context.setPositions(inpcrd.positions)

## Generate NMA-Scaled Flex Files
sAll = [[1, 10]]

simulation.addWorld(regionType='stretch',
                    region=sAll,
                    rootMobility='Weld',
                    timestep=0.004,
                    mdsteps=5,
                    argJointType='Pin',
                    subsets=['rama','side'],
                    samples=1)

# run simulation
simulation.step(5)
