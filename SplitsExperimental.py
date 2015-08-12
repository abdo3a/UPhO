#! /usr/bin/env python
import re
import os
from sys import argv
from math import fsum
import argparse

parser = argparse.ArgumentParser(description='This script to prune orthologs from gene trees. Input trees are provided  as a single newick file with one or more trees or a list of many input files')
parser.add_argument('-in', dest = 'Trees', type = str, default= None, nargs= '+',  help = 'file or files to prune wirth tree in newick format), required =False')
parser.add_argument('-iP', dest= 'inParalogs', type =str, default= 'True', help ='When True, inparalogues will  be included as orthologues, default = False')
parser.add_argument('-m', dest= 'minTaxa', type = int, default= '0', help ='Specify the minimum number of taxa to include in orthogroups')
parser.add_argument('-R', dest= 'Reference', type = str, default= 'None', help ='A fasta file with the source fasta sequences in the input tree. If provided, a fasta file will be created for each ortholog found')
parser.add_argument('-S', dest= 'Support', type = float, default = 0.0, help='Specify a minimum support value for the ortholog split.')
args = parser.parse_args()
#print args

#GLOBAL VARIABLES. MODIFY IF NEEDED
sep='|'
gsep=re.escape(sep)

#CLASS DEFINITIONS
class split():
    def __init__(self):
        self.vec =None
        self.covec=None
        self.branch_length=None
        self.support=None
        self.name=None
        
class myPhylo():
    '''A class for newick trees'''
    def __init__(self, N):
        self.leaves = get_leaves(N)
        self.splits = []
        self.ortho=[]
        self.costs={} # Dictionary of leaf cost for inparalog evaluation'
        self.newick = N
        for leaf in self.leaves:
             self.costs[leaf] = 1.0
        split_decomposition(self)   
#FUNCTION DEFINITIONS

def get_leaves(String):
    pattern = r"[(,]([A-Z _ a-z 0-9]+" + gsep + r"[0-9 A-Z a-z _ ]+)[:,)]"
    Leaves =re.findall(pattern, String)
    return Leaves

def spp_in_list(alist):
    '''return the species from a list of sequece identifiers'''
    spp = re.findall('([A-Z_a-z0-9]+)%s' %gsep , (',').join(alist))
    return spp
    
def complement(Sub, Whole):
    complement=[]
    for i in Whole:
        if i not in Sub:
            complement.append(i)
    return complement

def split_decomposition(Tree):
    '''Add a list of splits class objects to myPhylo Class objetc'''
    #Part I. Where we identify matching parenthesis in the newick.  
    newick = Tree.newick
    leaves = Tree.leaves
    P = {} #Empty dictionary where to store parenthesis identifiers and a list of string index.
    ids = 0
    idc =0
    Pos =0
    closed = []
    for l in newick:
        if l == '(':
            ids +=1
            P[ids]=[Pos]
        elif l ==')':
            idc = ids
            while idc in closed and idc != 0:
                idc = idc-1
                #print idc
            P[idc].append(Pos)
            closed.append(idc)
        Pos+=1
#    print P
#Part II: Where we use regex and to identify components of each split.
    for Key in P.iterkeys():
        r_vec=newick[P[Key][0]: P[Key][1]]
        vec = get_leaves(r_vec)
        covec = complement(vec, Tree.leaves)
        if not any (sorted(vec) == sorted(S.vec) or sorted(vec) == sorted(S.covec) for S in Tree.splits):
            mySplits = split()
            mySplits.vec = vec
            mySplits.covec = covec
            exp = re.escape(r_vec) + r'\)([0-9\.]+\:[0-9\.]+)'
            BranchVal=re.findall(exp, Tree.newick)
            if len(BranchVal) == 1:
                mySplits.branch_length = BranchVal[0].split(':')[1]
                mySplits.support = BranchVal[0].split(':')[0]
            Tree.splits.append(mySplits)
        else:
            print 'split already recognized'
    for leaf in leaves:
        vec=leaf
        covec = complement(vec,leaves)
        if not any (leaf == S.vec or leaf == S.covec for S in Tree.splits):
            mySplits =split()
            mySplits.vec = [vec]
            mySplits.covec = covec
            exp = re.escape(leaf) + r'\:([0-9\.]+)'
            BranchVal =  re.findall(exp, Tree.newick)
            if len(BranchVal) == 1:
                mySplits.branch_length = BranchVal[0]
            elif len(BranchVal) == 0:
                print 'The input tree h[as no branch values'
            else:
                print 'The terminal: %s  occurs %d times in the tree' % (leaf, len (BranchVals))
            Tree.splits.append(mySplits)
            
def LargestBox(LoL):
    '''Takes a list of list and returns a list where no list is a subset of the others, retaining only the largest'''
    NR =[]
    for L in LoL:
        score=0
        for J in LoL:
            if set(L).issubset(J):
                score +=1
        if score < 2:
            NR.append(L)
    return NR

def ortho_prune(Phylo, minTaxa):
    OrthoBranch = []
    for S in Phylo.splits:
        if S.support == None or S.support == '' or float(S.support) >= args.Support:
            for i_split in [S.vec, S.covec]:
                Otus = spp_in_list(i_split)
                if len(set(Otus))==len(Otus) and len(set(Otus)) >= minTaxa: # Eval orthologous split without inparalogues
                    if i_split not in OrthoBranch:
                        OrthoBranch.append(i_split)
                if  len(set(Otus)) == 1 and len(Otus) > 1: # find splits representing in-paralogs and update costs
                    for leaf in i_split:
                        ICost = 1.0/len(Otus)
                        if ICost < Phylo.costs[leaf]:
                            Phylo.costs[leaf] = ICost #Reduce count value of inparlogue copies in poportion to the number of inparalogs involved.
    if  args.inParalogs == 'True':
        for S in Phylo.splits:
            if S.support == None or S.support == '' or float(S.support) >= args.Support:
                for i_split in [S.vec, S.covec]:
                    Otus = spp_in_list(i_split)
                    cCount = fsum(Phylo.costs[i] for i in i_split)
                    if len(set(Otus)) == cCount and cCount >= minTaxa:
                        if i_split not in OrthoBranch:
                            OrthoBranch.append(i_split)
    orthos = LargestBox(OrthoBranch)
    Phylo.ortho=orthos

#MAIN
if __name__ == "__main__":
    OrList = open('UPhO_Pruned.txt', 'w')
    Total = 0
    for tree in args.Trees:
        name=tree.split('.')[0]
        count = 0
        with open(tree, 'r') as T:
            for line in  T:
                P = myPhylo(line)
                ortho_prune(P, args.minTaxa)
                ortNum=0
                for group in P.ortho:
                    FName= '#%s_%d,' %(name,ortNum)
                    G = ','.join(group)
                    G = G.strip(',')
                    OrList.write(FName + G + '\n')
                    count += 1
                    Total += 1
                    ortNum += 1
        print " %d orthogroups were found in the tree %s" % (count, tree)
    print 'Total  orthogroups found: %d' % Total
    OrList.close()
    if args.Reference != 'None':
        from BlastResultsCluster import retrieve_fasta
        print "Proceeding to create a fasta file for each ortholog"    
        retrieve_fasta( 'UPhO_Pruned.txt','uPhOrthogs','upho', args.Reference)
