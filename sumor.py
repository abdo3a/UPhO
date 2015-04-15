#! /usr/bin/env python
import os
import glob
import re
import shutil
import readline
import ete2
from sys import argv
#from matplotlib_venn import venn3, venn3_circles 

'''This script summarizes the distribution of orthologous by taxa.'''

readline.parse_and_bind("tab: complete")

def count_identifiers(file):
    Counter =0
    Handle = open(file, 'r')
    for line in Handle:
        if re.search(r'^>', line):
            Counter+= 1
    print counter


def min_leaves(infile, Quant):
    '''takes a file with one or more trees and return as file with the trees that have more pr equal leaves than the minimum specified by Quant'''
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

def header_writer():
    Output.write('OGnumber,Species_code,counSeq_Id\n')

def line_writer(P_attern):
    for file in glob.glob('*%s' % P_attern):
        Handle = open(file, 'r')
        OrtG = file.strip('%s' % P_attern)
        for line in Handle:
            if re.search (r'^>', line):
               Div = re.sub('>','',line).split('|')
               OutLine = '%s,%s,%s' % (OrtG, Div[0], Div[1])
               Output.write(OutLine)
        Handle.close()

def Set_of_FastaID(extension):
    '''This fuction inspect iteratively acrooss the composition of sequence identifiers of all files in the current directoty  (fasta sequence list, alignements and trees). Fisrt ocurrence of seqId sets are marked with the added extension '.2'. The collection of marked files constitue then non redundant collection of trees or sequences, based on seqIds only. Not: this function does not verifies identity in the whole file content (sequeces or topologies)   
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
    outgroup1 = 'H_pococki'
    outgroup2= 'S_lineatus'
    if T.get_leaves_by_name(outgroup1) != []:
        T.set_outgroup(outgroup1)
    else:
        T.set_outgroup(outgroup2)
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
            node.add_feature('name', I_node)
            I_node += 1
    for node in T.traverse():
        OG_count= len(node.OgCompo)
        node.add_feature('Total', OG_count)
    return T

def CdsSets_by_Treatment(treat):
    D1 = open(treat, 'r')
    Set =[]
    for line in D1:
        if  not line.startswith('OGnumber'):
            list=line.split(',')
            element = list[1] + list[2]
            Set.append(element)
    return Set

def get_orthoSet_by_node(Phylo, NodeNumber):
    T = Phylo
    N = T&NodeNumber
    Compo = N.OgCompo
    return Compo


def tree_plot(phylo, Bsize = 1.0, Fig = False ):
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
    if Fig == True:
         T.render(OutName, tree_style = ts)
    else:
        T.show(tree_style=ts)

##### YEAH_SHOWDOWN ######

Q = raw_input("Run interatctively (y/n)? ")
print "This script will help us annotate a phylogenies, from a colection of fasta (orthologs) .Select from the following options"
T = None
while Q == 'y':
    if T == None:
        print "No trees in the oven"
    else:
        print  T.get_ascii(attributes=["node_number", "name"], show_internal=True)
        
    print """Select from the following options:
    
        1: Create a OG_sumary file
        2: Annotate and plot (see) the tree.
        3: Save  current tree image or load and savea new tree to image file (PDF, SVG or PNG).
        4: Query the composition on specific node (requires loaded tree).
        5: Store treatment compositions to ompare them later.

        q: Exit
        
        """
    selection = raw_input("Enter your selection: ")
    if selection  not in ['1','2','3','4', '5', 'q']:
        print "ERROR type the number of your selection"
    elif selection == '1':
        W_path = raw_input('Select the Path to process: ')
        Pattern = raw_input('Type the extension of files to process: ')
        os.chdir(W_path)
        Output = open('OG_summary.csv', 'w')
        header_writer()
        line_writer(Pattern)
        print "Orthology composition written to %s" % Output
        Output.close()
    elif selection == '2':
        Tree = raw_input('Input name of tree file (newick): ')
        Summary = raw_input('Input OG_summary file: ')
        T = tree_ortho_annotator(Summary, Tree)
        B_size=  float(raw_input('Bubble ize factor: '))
        tree_plot(T, B_size)
        
    elif selection== '3':
        if T == 0:
            Tree = raw_input('Input name of tree file (newick): ')
            Summary = raw_input('Input OG_summary file: ')
            B_size=  float(raw_input('Bubble ize factor: '))
            name = raw_input('Name of otput image file: ')
            Type = raw_input('Type of file (pdf, svg, or  png: ')
            OutName = name + '.' + Type
            T = tree_ortho_annotator(Summary, Tree) 
            tree_plot(T, B_size, Fig=True)
        else:
            name = raw_input('Name of otput image file: ')
            Type = raw_input('Type of file (pdf, svg, or  png: ')
            OutName = name + '.' + Type
            tree_plot(T, B_size, Fig=True)
    elif selection=='4':
        print "En consytruccion"

    elif selection=='q':
        Q = False
    break
