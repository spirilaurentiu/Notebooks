from robosample import *

# Load Amber files
prmtop = AmberPrmtopFile("mproA/ligand.prmtop")
inpcrd = AmberInpcrdFile("mproA/ligand.rst7")

# Hardware platform
platform = Platform.getPlatformByName('GPU')

properties={'nofThreads': 0}

# Create a Robosample system by calling createSystem on prmtop
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


simulation = Simulation(prmtop.topology, system, integrator, platform, properties)
simulation.reporters.append(PDBReporter('temp', 1))
simulation.context.setPositions(inpcrd.positions)

## Generate NMA-Scaled Flex Files
sAll = [[1, 306]]
#simulation.addWorld(regionType='roll', region=s1_5,  rootMobility='Free', timestep=0.003, mdsteps=10, argJointType='Pin', subsets=['rama'], samples=1)
#simulation.addWorld(regionType='stretch', region=nter,  rootMobility='Free', timestep=0.004, mdsteps=40, argJointType='Pin', subsets=['rama', 'side'], samples=6)
simulation.addWorld(regionType='stretch', region=sAll,  rootMobility='Weld', timestep=0.004, mdsteps=5, argJointType='Pin', subsets=['rama','side'], samples=10, contacts=False, contactCutoff=2)
#simulation.addWorld(regionType='coils', region=s1_278,  rootMobility='Free', timestep=0.002, mdsteps=5, argJointType='Pin', subsets=['all'], samples=9, contacts=True, contactCutoff=2)
#simulation.addWorld(regionType='loops', rootMobility='Free', timestep=0.004, mdsteps=30, argJointType='Pin', subsets=['rama'], samples=1)
#simulation.addWorld(regionType='accesible', rootMobility='Weld', timestep=0.004, mdsteps=30, argJointType='Pin', subsets=['side'], samples=1)

# run simulation
simulation.step(5)

