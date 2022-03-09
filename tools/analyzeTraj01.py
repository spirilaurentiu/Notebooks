# Robosample tools
import sys, os, glob
import numpy as np
import scipy 
import scipy.stats
import argparse

#from scipy.signal import find_peaks
import scipy.signal as scisig

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from logAnalyzer import LogAnalyzer
from trajAnalyzer import TrajectoryAnalyzer
from autocorFuncs import *
from jumpDetect import *

def print1DNPArray(series):
	print("\n")
	for k in range(series.shape[0]):
		print(series[k], end = ' ')
		if k % 80 == 79:
			print("\n")
	print("\n")
#

parser = argparse.ArgumentParser()
parser.add_argument('--simDirs', default=None, nargs='+',
	help='Directory with input data files')
parser.add_argument('--logDirs', default=None, nargs='+',
	help='Directory with input data files')
parser.add_argument('--molName', default=None, 
	help='Molecule name also the name of the directory of the prmtop file.')
parser.add_argument('--FNSeeds', default=None, nargs='+',
	help='Name root for first input data files')
parser.add_argument('--skip_header', default=0, type=int,
	help='# of lines to be skipped by numpy.loadtxt from the beggining')
parser.add_argument('--skip_footer', default=0, type=int,
	help='# of lines to be skipped by numpy.loadtxt at the end')
parser.add_argument('--datacols', default=0, type=int, nargs='+',
	help='Columns to be read by numpy.loadtxt')
parser.add_argument('--stride', default=1, type=int,
	help='Stride for the read lines.')
parser.add_argument('--nbins', default=50, type=int,
	help='Number of bins for histograms. Default for 7.2 spacing')
parser.add_argument('--analyze', default=[], nargs='+', 
	help='Decide what to analyze')

parser.add_argument('--distance', default=[0, 1], type=int, nargs='+',
	help='Atom indeces to compute distance for.')

parser.add_argument('--Ms', default=[0], type=int, nargs='+', 
	help='Number of steps to sum the correlation function on. One M per column')
parser.add_argument('--fitacf', action='store_true', default=False,
	help='Fit autocorrelation function to an exponential')
parser.add_argument('--acf', action='store_true', default=False,
	help='Compute autocorrelation function.')
parser.add_argument('--bse', action='store_true', default=False,
	help='Use block averaging')
parser.add_argument('--nofAddMethods', default=0, type=int,
	help='Number of additional methods wrote by James on StackOverflow.')
parser.add_argument('--logDiffWin', default=3, type=int,
	help='Moving difference window.')
parser.add_argument('--trajDiffWin', default=3, type=int,
	help='Moving difference window.')
parser.add_argument('--accMAWin', default=3, type=int,
	help='Moving average window.')
parser.add_argument('--accDiffWin', default=3, type=int,
	help='Moving difference window.')
parser.add_argument('--makeplots', default=[], nargs='+', 
	help='Make plots')
parser.add_argument('--savefigs', action='store_true', default=False,
	help='Save the plot into a file')
args = parser.parse_args()
# General plot parameters
colors = ['red', 'orange', 'magenta', 'cyan', 'green', 'pink']

#from pymbar import timeseries as ts
#from pymbar.utils import ParameterError

nofSeeds = len(args.FNSeeds)
if nofSeeds % 3:
	print(args.FNSeeds)
	print("Nof seeds must be divisible by 3. Exiting...")
	exit(1)

nofParamSets = nofSeeds // 3

# [[s1 s2 s3], [s4 s5 6]]
seeds = np.array(np.array_split(np.array([int(seed) for seed in args.FNSeeds]) , nofParamSets))
print(seeds)

runningData = np.empty((3990))
runningStd = np.empty((3990))
TA = []
fignum = -1
if "traj" in args.analyze:
	for diri in range(len(args.simDirs)):
		# Analyze trajectory
		TA.append(TrajectoryAnalyzer( (args.molName + '/ligand.prmtop'), args.molName, args.FNSeeds, [args.simDirs[diri]] ))
		#TA.ReadPdbs(verbose = False)
		TA[diri].ReadDcds(verbose = True)
		TA[diri].Distance(np.array([[args.distance[0], args.distance[1]]]))
	
	#	TA.RMSD() TA.RG() TA.SASA() TA.Helicity()

	# Put data in Numpy array: dim1 is dir, dim2 is seed, dim3 is data
	# seed 0 dir 0 --------
	# seed 0 dir 1 --------
	# seed 1 dir 0 --------
	# seed 1 dir 1 --------
	# seed 2 dir 0 --------
	# seed 2 dir 1 --------
	data = []
	dim1ix = -1
	for seedi in range(len(args.FNSeeds)):
		for diri in range(len(args.simDirs)):
			dim1ix += 1
			#print("dir", diri, args.simDirs[diri])
			#print("seedi to seed", seedi, args.FNSeeds[seedi])
			print("append TA[", args.simDirs[diri], "].data[", args.FNSeeds[seedi], "]")
			#print(TA[diri].data[seedi].flatten())
			data.append(TA[diri].distances[seedi].flatten())

	# Get maximum length
	lens = [len(datum) for datum in data]
	
	# Put data in a Numpy array with maximum dimensions
	npdata = np.empty((len(data), max(lens))) * np.nan
	for i in range(len(data)):
		for j in range(len(data[i])):
			npdata[i, j] = data[i][j]
	data = npdata
	print("data shape", data.shape)
	print("data")
	print(data)

	# Calculate
	pltNofRows = 2
	pltNofCols = 1

	nofSimsPerParamSet = int(data.shape[0] / nofParamSets)
	print("There are", nofSimsPerParamSet, "simulations per parameter set.")
	runningBias = np.empty(data.shape)
	runningData = np.empty(data.shape)
	runningStd = np.empty(data.shape)
	print("nofParamSets", nofParamSets)
	print("data.shape", data.shape)
	bias = np.empty((nofParamSets, data.shape[1]))
	mofm = np.empty((nofParamSets, data.shape[1]))
	sofm = np.empty((nofParamSets, data.shape[1]))

	# Get the true value estimate (last average of the longest simulations)
	lastValues = []
	for datumi in range(data.shape[0]):
		if not np.isnan(data[datumi][-1]):
			lastValues.append(data[datumi][-1])
	trueValueEst = np.mean(lastValues)
	print("trueValueEst", trueValueEst)

	# Get running means
	fig, axs = plt.subplots(pltNofRows, pltNofCols)
	for paramSeti in range(nofParamSets):
		startSim = paramSeti * nofSimsPerParamSet
		print("Parameter set ", paramSeti, "with seeds", seeds[paramSeti])
		for framei in range(0, data.shape[1]):
			paramSetSimsRange = range(startSim, nofSimsPerParamSet + startSim)
			for simi in paramSetSimsRange:
				# Make sure the current frame is not empty
				if data[simi, framei] != None:
					runningData[simi, framei] = data[simi, framei]
					runningBias[simi, framei] = (data[simi, framei] - trueValueEst)**2
					runningStd[ simi, framei] = np.std(data[simi, 0:framei+1])
		
			#print("runningData.shape", runningData.shape)
			# Choose includedSims
			#includedSims = paramSetSimsRange
			includedSims = []
			for simi in paramSetSimsRange:
				if data[simi, framei] != None:
					includedSims.append(simi)
			bias[paramSeti, framei] = np.mean(runningBias[includedSims, framei])
			mofm[paramSeti, framei] = np.mean(runningData[includedSims, framei])
			sofm[paramSeti, framei] = np.std(runningData[includedSims, framei])


	print("Plotting running means and stds")
	colors = ['black', 'red']
	for paramSeti in range(nofParamSets):
		startSim = paramSeti * nofSimsPerParamSet
		for simi in range(startSim, nofSimsPerParamSet + startSim):

			X = range(0, runningData.shape[1])
			Y = runningData[simi]
			axs[0].plot(X, Y, color = colors[paramSeti])
			axs[0].set_title('Running Means ' + args.molName)

			#Y = runningBias[simi]
			#Y = bias[paramSeti]
			#axs[1].plot(X, Y, color = colors[paramSeti])
			#axs[1].set_title('Running Error')

			Y = mofm[paramSeti]
			Yerr = sofm[paramSeti]
			#Yerr = (sofm[paramSeti])**2 + (bias[paramSeti])**2
			axs[1].errorbar(X, Y, yerr=Yerr, color = colors[paramSeti], errorevery = 100, elinewidth = 0.5)
			axs[1].set_title('Std of Means ' + args.molName)
			axs[1].legend()

			#Yerr = 
			#axs[1, 0].errorbar(X, Y, yerr=Yerr, label=str(paramSeti))

		
		# Plot trajectory based geometric functions
	#	figsPerSeed = 3
	#	figs = [None] * len(args.FNSeeds) * figsPerSeed
	#	axes = [None] * len(args.FNSeeds) * figsPerSeed
	#	for seedi in range(nofSeeds):
	#		if(('traj' in args.makeplots) or ('all' in args.makeplots)):
	#			fignum += 1
	#			figIx = (seedi * 2) + fignum
	#			figs[figIx], axes[figIx] = plt.subplots(2, 1)
	#			plt.suptitle('Seed ' + str(args.FNSeeds[seedi]))
	#	
	#			series = [TA.data[seedi]]
	#			seriesLabels = ['Distance']
	#			for si in range(len(series)):
	#				axes[figIx][si].plot(series[si], label=seriesLabels[si], color='black')
				
	#			# 
	#			fignum += 1
	#			figIx = (seedi * figsPerSeed) + fignum
	#			figs[figIx], axes[figIx] = plt.subplots(2, 2)
	#			plt.suptitle('Seed ' + str(args.FNSeeds[seedi]))
	#	
	#			series = [TA.rmsds[seedi], TA.RGs[seedi], TA.helicities1[seedi], TA.totSASAs[seedi]]
	#			seriesLabels = ['RMSD', 'RG', 'Helicity', 'SASA']
	#			for si in range(len(series)):
	#				axes[figIx][int(si/2), (si%2)].plot(series[si], label=seriesLabels[si], color='black')
	#	
	#				# PLot difference quotient of acceptance
	#				toBePlotted = difference_quotient(series[si], args.trajDiffWin)
	#				scaleFactor = np.abs(np.mean(series[si])) / np.abs(np.mean(toBePlotted)) / 30.0
	#				toBePlotted = scaleFactor * toBePlotted
	#				#axes[figIx][int(si/2), (si%2)].plot(toBePlotted, label=seriesLabels[si] + 'diffQuot', color='pink')
	#	
	#				# Plot diff quatioent X intercept
	#				XAxisIntersections = intersections(toBePlotted, np.zeros((toBePlotted.size)))
	#				if XAxisIntersections.size:
	#					XAxisIntersections = XAxisIntersections - 0
	#					print("eqPoint(" + seriesLabels[si] + ")", XAxisIntersections[0])
	#				zeroArray = np.zeros((XAxisIntersections.size))
	#				axes[figIx][int(si/2), (si%2)].scatter(XAxisIntersections, zeroArray, label=seriesLabels[si] + 'diffQuot0s', color='red')
	#				axes[figIx][int(si/2), (si%2)].legend()
	#	
	#			#axes[figIx][1, 1].scatter( TA.totSASAs[seedi], TA.RGs, \
	#			#	label='SASA vs RG', s = 1**2, cmap='PuBu_r')
	#			#axes[figIx][1, 1].legend()



if args.makeplots:
	plt.legend()
	plt.show()
#
#
