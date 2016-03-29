#! /usr/bin/env python
import os
#from joblib import Parallel, delayed  
#import multiprocessing
import glob
import re
import shutil
import readline
import ete2

'''This script contains functions to summarize the distribution of orthologous on a tree and auxiliary functions. These functions can be imported into the interpreted and ran interactively or accessed through a helper script.'''

readline.parse_and_bind("tab: complete")
#Global Variables. Modify if needed.

Separator = '|'
outgroups = []

#Function definitions

def count_identifiers(file):
    Counter =0
    Handle = open(file, 'r')
    for line in Handle:
        if re.search(r'^>', line):
            Counter+= 1
    print counter


def min_leaves(infile, Quant):
    '''takes a file with one or more trees and return as file with the trees that have more or equal leaves than the minimum specified by Quant'''
    with open(infile, 'r') as F:
        OutName = infile.split('.')[0] + str(Quant) +'.' + infile.split('.')[1]
        Out = open(OutName, 'w')
        for Line in F:
            #print Line
            if Line.startswith('(') and Line.endswith(';\n'): #simple check if line looks like a
                Leaves = re.findall(r"[A-Z_a-z]+", Line)
                #print Leaves
                if len(set(Leaves)) >= int(Quant):
                    Out.write(Line)
    F.close()
    Out.close()


def RemoveDupSpecies(Tree):
    '''This function takes a tree gene tree with many genes copies per species, and returns a tree with one leaf per  species. Retaining only one sequence per species'''
    Out = open('all_ready.tre','w')
    with open(Tree, 'r') as F:
        for line in F:
            Sps=[]
            T = ete2.Tree(line)
            for leaf in T.iter_leaves():
                sp = leaf.name.split('|')[0]
                if sp not in Sps:
                    leaf.name=sp
                    Sps.append(sp)
            T.prune(Sps)
            Tn=T.write( format = 0)
            Out.write(Tn + '\n')

def MakeAstralSpeciesMap(All):
    '''Creates a list of species and its gene copies for Astral. Note: as for May 2015, this function produces as seemingly correct map[ file, however it fails to run in astral. Maybe memory leak in Astral4.4.7'''
    with open(All, 'r') as F:
        Sps={}
        for L in F:
            T = ete2.Tree(L) 
            for leaf in T.iter_leaves():
                sp, seq = leaf.name.split(Separator)
                if sp not in Sps.keys():
                    Sps[sp]=[leaf.name]
                    leaf.name = sp
                else:
                    Sps[sp].append(leaf.name)
    Out = open('Species_map.txt', 'w')
    for k in Sps.iterkeys():
        Sps[k]= set(Sps[k])
        Out.write(k + ': ' + ','.join(Sps[k]) + '\n')

        
def deRedundance(LoL):
    '''Takes a list of list and returns a list where no list is a subset of the others'''
    NR =[]
    for L in LoL:
        score=0
        for J in LoL:
            if set(L).issubset(J):
                score +=1
        if score <2:
            NR.append(L)
    return NR



def line_writer(P_attern):
    '''Creates OG summary file, for Tree orthology annotation from tree files in current working directory.'''
    Output = open('OG_summary.csv', 'w')
    Output.write('OGnumber,Species_code,Seq_Id\n')
    for file in glob.glob('*%s' % P_attern):
        Handle = open(file, 'r')
        OrtG = file.strip('%s' % P_attern)
        for Line in Handle:
            if re.search (r'^>', Line):
                Line = Line.strip('\n')
                Line = re.sub(' ', Separator, Line) # unique sequence identifiers should not conatain spaces and this data will not be included in the annotation.
                Div = re.sub('>','',Line).split(Separator)
                OutLine = '%s,%s,%s\n' % (OrtG, Div[0], Div[1])
                Output.write(OutLine)
        Handle.close()
    Output.close()

def Set_of_FastaID(extension):
    '''This function inspect iteratively across the composition of sequence identifiers of all files in the current directory  (fasta sequence list, alignments and trees). First occurrence of seqId sets are marked with the added extension '.2'. The collection of marked files constitute then non redundant collection of trees or sequences, based on seqIds only. Not: this function does not verifies identity in the whole file content (sequences or topologies)   
'''
    Report = open('redundancyReport.txt', 'w')
    UniqComsId = []
    setsInspected = []
    for File in glob.glob('*%s' % extension):
        Handle = open(File, 'r')
        IdsinFile=[]
        for line in Handle:
            if line.startswith('>'):
                FastaId = line.strip('>')
                FastaId = FastaId.replace('\n', '')
                IdsinFile.append(FastaId)
            elif line.startswith('('):
                IdsinFile= re.findall(r'[A-Z]_[a-z]+\|[a-z , 0-9, _]+', line)           
                IdsinFile = sorted(IdsinFile)
        if IdsinFile not in setsInspected:
            UniqComsId.append(File)
            setsInspected.append(IdsinFile)
            shutil.copyfile(File, File + '.2')
        else:
            Index = setsInspected.index(IdsinFile)
            AlreadySet = UniqComsId[Index]
            Report.write('The FastaId compososition of %r is represented in file %r' % (File, AlreadySet))
        Handle.close()
    Report.write('The are %d different groups' % len(UniqComsId))
    Report.write(UniqComsId)

def tree_ortho_annotator(summary, phylo):
    inFile= open(summary, 'r')
    T = ete2.Tree(phylo)
    idx =0
    if outgroups:
        for i in outgroups:
            if T.get_leaves_by_name(outgroups[idx]) != []:
                T.set_outgroup(outgroups[idx])
                break
    for node in T.traverse():
        node.add_feature('OgCompo', []) #initialize the OrthoGroup (OG) composition in each node
    for line in inFile: #pasre the OG summary file and add the OG composition to each leaf
        if not re.search('^OGnumber', line):
            items= line.split(',')
            Sp_Code = items[1]
            OG_num = items[0]
            CNode = T&Sp_Code #get leaf node
            CCompo = CNode.OgCompo #access the list compositon of each leaf
            if OG_num not in CCompo: # conditional to avoid count twice the same orthogroup per leaf, which occurs when there are inParalogs
                CCompo.append(OG_num)
                CNode.add_feature('OgCompo', CCompo)
    I_node = 0 #initialize counter to use as node name
    for node in T.traverse():
        if node.is_leaf() == False and node.is_root() == False:
            Left = node.children[0]
            Right = node.children[1]
            Outs =  set(T.get_leaves()) - set(node.get_leaves())
            Lun = []
            Run = []
            Oun = []
            for leaf in Left.iter_leaves():
                Lun= set(Lun) | set(leaf.OgCompo)
            for leaf in Right.iter_leaves():
                Run= set(Run) | set(leaf.OgCompo)
            for Sp in Outs:
                leafN =Sp.name
                leaf = T&leafN
                Oun= set(Oun) | set(leaf.OgCompo)
            Inter = set(Lun) & set (Run) & set(Oun)
            node.add_feature('OgCompo', Inter)
            node.add_feature('name', str(I_node))
            I_node += 1
    for node in T.traverse():
        OG_count= len(node.OgCompo)
        node.add_feature('Total', OG_count)
    return T

def orthologs_in_file(OGsummary):
    '''Make a set of sequence identifiers from  OG summary file for comparisons between OG compositions'''
    D1 = open(OGsummary, 'r')
    Seqs =[]
    for line in D1:
        if  not line.startswith('OGnumber'):
            list=line.split(',')
            element = list[1] + Separator + list[2]
            Seqs.append(element)
    return set(Seqs)

def get_orthoSet_by_node(Phylo, NodeNumber):
    T = Phylo
    N = T&"%s"% NodeNumber
    Compo = N.OgCompo
    return Compo


def tree_plot(phylo, Bsize = 1.0):
    T = phylo
    ts = ete2.TreeStyle()
    ts.show_leaf_name = False
    for n in T.traverse():
        if n.is_leaf():
            Nlabel = ete2.AttrFace('name', fsize =14, ftype='Arial', fstyle='italic')
            n.add_face(face =Nlabel,column=0, position ='aligned')
        NOg = ete2.AttrFace('Total', fsize= 10, ftype='Arial') 
        n.add_face(face=NOg,column=0, position =  'branch-bottom')
        #Set node style
        nstyle = ete2.NodeStyle()
        nstyle["fgcolor"] = 'Red'
        nstyle["shape"] = "circle"
        nstyle["hz_line_color"]="Gray"
        nstyle["hz_line_width"]=2
        nstyle["vt_line_width"]=2
        nstyle["vt_line_color"]="Gray"
        nstyle["size"] = n.Total * Bsize
        n.set_style(nstyle)
    return ts
