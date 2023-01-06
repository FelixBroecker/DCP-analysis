#!/bin/env python3

import subprocess

from pyscript import *
import numpy as np
import re

def read_trajectory_ami(search):
    with open(f'trajectory.ami', 'r') as reffile:
        if search == 'count':
            for line in reffile:
               if 'count' in line:
                   count = int(re.search(r'\d+', line).group())
                   break
            return(count)
        if search == 'file':
            for line in reffile:
                if 'file' in line:
                    name = re.search(r'file=([\'"]?)(.+?)\.wf\1', line).group(2)
                    break
            return(name)
        
        
def reading_saddlepoint_calculation_in(search):
    with open('saddlepoint_calculation.in', 'r') as reffile:
        found = False
        for line in reffile:
            if search in line:
                found = True
                words = line.split()
                try:
                    float(words[1])
                    is_float = True
                except ValueError:
                    is_float = False
                if is_float:
                    return(float(words[1]))
                else:
                    return(words[1])
        #default values if not defined in .in file
        if not found:
            if search == 'threshold_DCP_guess':
                return(1e-1)
            if search == 'method':
                return('gradient_norm')
            if search  == 'deflection_factor':
                return(3e-3)
        
        
def reading_n_elecs():
    with open(f'trajectory-1-max.ref', 'r') as reffile:
        line = reffile.readline()
        while 'MAX:' not in line:
            line = reffile.readline()
        line = reffile.readline()
        words = line.split()
        n_elecs = int(words[0])
    return n_elecs


def reading_coordinates(trajectory, calculation_type):
    if calculation_type == method:
        path = f'trajectory-{trajectory}/DCP_{method}/fort.100'
    elif calculation_type == 'stedes_eigvec':
        path = f'eigenvector_check/fort.100'
    with open(path) as reffile:
            R = []
            for line in reffile:
                if 'after minimize:' in line:
                    line = reffile.readline()
                    line = reffile.readline()
                    for _ in range(n_elecs):
                        line = reffile.readline()
                        words = line.split()
                        for word in words[1:]:
                            R.append(float(word))
    return(np.array(R))


def read_eigenvector(trajectory, n_th):
    with open(f'trajectory-{trajectory}/DCP_newton/fort.100') as reffile:
        R = []
        for line in reffile:
            found = True
            if 'hessian eigenvalues and -vectors' in line:
                line = reffile.readline()
                for _ in range (n_th - 1):
                    for _ in range(n_elecs):
                        line = reffile.readline()
                    line = reffile.readline()
                for _ in range(n_elecs):
                    line = reffile.readline()
                    coordinates = line.split()
                    for coordinate in coordinates[1:]:
                        R.append(float(coordinate))
    return np.array(R)


def deflection_saddlepoint(eigenvector, saddlepoint, deflection_factor):
    return(eigenvector * deflection_factor + saddlepoint)


def phi_value(trajectory, path, search):
    with open(path) as reffile:
        found = False
        for line in reffile:
            if search in line:
               found = True
               words = line.split()
               phi = float(words[1])
        if not found:
            print(f'Phi from {path} was not found')
    return phi


def compare_position(R1, R2, threshold_molecule):
    norm = np.linalg.norm(R1 - R2)
    if norm <= threshold_molecule:
        return(True)
    else:
        return(False)
    
    
def newton(trajectory, molecule, R, folder_path, ProcessMaxima = False):
    cp(f'{name}.wf', f'{folder_path}')
    with open(f'{folder_path}/newton.ami', 'w') as printfile:
        printfile.write(f'''! seed for random number generation, not important
$gen(seed=101)
! reading the wave function file
$wf(read,file='{name}.wf')
$init_rawdata_generation()
$init_max_search(
step_size=0.1,
correction_mode=none,
singularity_threshold=0.0001,
method=newton,
verbose=2,
negative_eigenvalues=-1,
eigenvalue_threshold=1e-10)
! setting the initial position
$init_walker(
free
''')
        for s in range(n_elecs):
            for t in R[s*3:s*3+3]:
                printfile.write(f'{t} ')
            printfile.write('\n')
        printfile.write(''')
$sample(create, size=1, single_point)
! maximize the walker
$maximize_sample()''')

    if ProcessMaxima:
        with open(f'{folder_path}/cluster.yml', 'w') as printfile:
            printfile.write(f'''--- # MaximaProcessing
MaximaProcessing:
  binaryFileBasename: stedes
  calculateSpinCorrelations: false
  shuffleMaxima: false
...''')

    #makes the amolqc run for the minimum single point calculation
    with cd(folder_path):
        run('amolqc newton.ami')
        if ProcessMaxima:
            run('ProcessMaxima cluster.yml')
    return(print(f'newton for {folder_path} for trajectory-{trajectory} was calculated'))
    

#script starts here
trajectory = int(input('Which trajectory do you mean?'))

n_elecs = reading_n_elecs()
method = reading_saddlepoint_calculation_in('method')
name = read_trajectory_ami('file')
deflection_factor = int(input('What is the deflection_factor ?'))

mkdir(f'trajectory-{trajectory}/DCP_{method}/reduce_order')
eigenvector = read_eigenvector(trajectory, 2) 
saddlepoint = reading_coordinates(trajectory, method)
deflected_saddlepoint = deflection_saddlepoint(eigenvector, saddlepoint, deflection_factor)
newton(trajectory, name, deflected_saddlepoint, f'trajectory-{trajectory}/DCP_{method}/reduce_order', True)

print(f'newton calculation with deflection_factor of {deflection_factor} was done.')