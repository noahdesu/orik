#!/usr/bin/env python

'''
dumpers_c4.py
   Methods for dumping specific contents from the database.
'''

import inspect, os, sys

# ------------------------------------------------------ #
# import sibling packages HERE!!!
if not os.path.abspath( __file__ + "/../.." ) in sys.path :
  sys.path.append( os.path.abspath( __file__ + "/../.." ) )

from utils import tools, dumpers
# ------------------------------------------------------ #

#############
#  GLOBALS  #
#############
DUMPERS_C4_DEBUG = tools.getConfig( "DEDT", "DUMPERS_C4_DEBUG", bool )


#############
#  DUMP IR  #
#############
# dump the contents of an entire IR database
def dumpIR( cursor, db_dump_save_path ) :

  # get facts
  cursor.execute( "SELECT fid FROM Fact" )
  fid_all = cursor.fetchall()
  fid_all = tools.toAscii_list( fid_all )

  full_facts = []
  for fid in fid_all :
    full_facts.append( dumpSingleFact_c4( fid, cursor ) )

  # get rules
  cursor.execute( "SELECT rid FROM Rule" )
  rid_all = cursor.fetchall()
  rid_all = tools.toAscii_list( rid_all )

  full_rules = []
  for rid in rid_all :
    full_rules.append( dumpSingleRule_c4( rid, cursor ) )

  # get clock
  full_clock = dump_clock( cursor )

  if db_dump_save_path :
    if DUMPERS_C4_DEBUG :
      print "...DUMPING IR..."
      print full_facts
      print full_rules
      print full_clock

    # save to file
    fo = open( db_dump_save_path, "w" )
    for fact in full_facts : # write facts
      fo.write( fact )
    for rule in full_rules : # write rules
      fo.write( rule )
    for clock in full_clock : # write clock facts
      fo.write( clock )
    fo.close()

    print "IR DUMP SAVED TO : " + db_dump_save_path

  else :
    print "...DUMPING IR..."
    print full_facts
    print full_rules
    print full_clock


#########################
#  DUMP SINGLE FACT C4  #
#########################
# input fid and IR db cursor
# output a single fact

def dumpSingleFact_c4( fid, cursor ) :
  fact = ""

  cursor.execute( "SELECT name FROM Fact WHERE fid == '" + fid + "'" ) # get fact name
  factName    = cursor.fetchone()
  factName    = tools.toAscii_str( factName )

  # get list of attribs in fact
  factList    = cursor.execute( "SELECT attName FROM FactAtt WHERE fid == '" + fid + "'" ) # list of fact atts
  factList    = cursor.fetchall()
  factList    = tools.toAscii_list( factList )

  # get fact time arg
  #factTimeArg = ""
  #cursor.execute( "SELECT timeArg FROM Fact WHERE fid == '" + fid + "'" )
  #factTimeArg = cursor.fetchone()
  #factTimeArg = tools.toAscii_str( factTimeArg )

  # convert fact info to pretty string
  fact += factName + "("
  for j in range(0,len(factList)) :
    if j < (len(factList) - 1) :
      fact += factList[j] + ","
    else :
      fact += factList[j]
  #if not factTimeArg == "" :
  #  fact += "," + factTimeArg

  fact += ");" + "\n" # end all facts with a semicolon

  return fact


#########################
#  DUMP SINGLE RULE C4  #
#########################
# input rid and IR db cursor
# output a single rule

def dumpSingleRule_c4( rid, cursor ) :

  rule = ""

  # -------------------------------------------------------------- #
  #                           GOAL                                 #

  # get goal name
  cursor.execute( "SELECT goalName FROM Rule WHERE rid == '" + rid + "'" ) # get goal name
  goalName    = cursor.fetchone()
  goalName    = tools.toAscii_str( goalName )

  # get list of attribs in goal
  goalList    = cursor.execute( "SELECT attName FROM GoalAtt WHERE rid == '" + rid + "'" )# list of goal atts
  goalList    = cursor.fetchall()
  goalList    = tools.toAscii_list( goalList )

  # get goal time arg
  goalTimeArg = ""
  cursor.execute( "SELECT goalTimeArg FROM Rule WHERE rid == '" + rid + "'" )
  goalTimeArg = cursor.fetchone()
  goalTimeArg = tools.toAscii_str( goalTimeArg )

  # convert goal info to pretty string
  rule += goalName + "("
  for j in range(0,len(goalList)) :
    if j < (len(goalList) - 1) :
      rule += goalList[j] + ","
    else :
      rule += goalList[j] + ")"
  if not goalTimeArg == "" :
    #rule += "@" + goalTimeArg + " :- "
    sys.exit( "ERROR: leftover timeArg in goal: " + rule + "@" + goalTimeArg )
  else :
    rule += " :- "

  # --------------------------------------------------------------- #
  #                         SUBGOALS                                #

  # get list of sids for the subgoals of this rule
  cursor.execute( "SELECT sid FROM Subgoals WHERE rid == '" + str(rid) + "'" ) # get list of sids for this rule
  subIDs = cursor.fetchall()
  subIDs = tools.toAscii_list( subIDs )

  # prioritize dom subgoals first.
  subIDs = prioritizeDoms( rid, subIDs, cursor )

  # prioritize negated subgoals last.
  subIDs = prioritizeNegatedLast( rid, subIDs, cursor )

  subTimeArg = None
  # iterate over subgoal ids
  for k in range(0,len(subIDs)) :
    newSubgoal = ""

    s = subIDs[k]

    # get subgoal name
    cursor.execute( "SELECT subgoalName FROM Subgoals WHERE rid == '" + str(rid) + "' AND sid == '" + str(s) + "'" )
    subgoalName = cursor.fetchone()

    if not subgoalName == None :
      subgoalName = tools.toAscii_str( subgoalName )

      if DUMPERS_C4_DEBUG :
        print "subgoalName = " + subgoalName


      # get subgoal attribute list
      subAtts = cursor.execute( "SELECT attName FROM SubgoalAtt WHERE rid == '" + rid + "' AND sid == '" + s + "'" )
      subAtts = cursor.fetchall()
      subAtts = tools.toAscii_list( subAtts )

      # get subgoal time arg
      cursor.execute( "SELECT subgoalTimeArg FROM Subgoals WHERE rid == '" + rid + "' AND sid == '" + s + "'" )
      subTimeArg = cursor.fetchone() # assume only one time arg
      subTimeArg = tools.toAscii_str( subTimeArg )

      #if goalName == "pre" and subgoalName == "bcast" :
      #  print "............................................"
      #  print dumpers.reconstructRule( rid, cursor )
      #  print "subgoalName = " + subgoalName
      #  print "subAtts     = " + str( subAtts )
      #  print "subTimeArg  = " + str( subTimeArg )
      #  tools.bp( __name__, inspect.stack()[0][3], "stuff" )

      # get subgoal additional args
      cursor.execute( "SELECT argName FROM SubgoalAddArgs WHERE rid == '" + rid + "' AND sid == '" + s + "'" )
      subAddArg = cursor.fetchone() # assume only one additional arg
      if not subAddArg == None :
        subAddArg = tools.toAscii_str( subAddArg )
        subAddArg += " "
        newSubgoal += subAddArg

      # all subgoals have a name and open paren
      newSubgoal += subgoalName + "("

      # add in all attributes
      for j in range(0,len(subAtts)) :

        currAtt = subAtts[j]

        # replace SndTime in subgoal with subTimeArg, if applicable
        if not subTimeArg == "" and "SndTime" in currAtt :
          currAtt = str( subTimeArg )

        if j < (len(subAtts) - 1) :
          newSubgoal += currAtt + ","
        else :
          newSubgoal += currAtt + ")"

      # cap with a comma, if applicable
      if k < len( subIDs ) - 1 :
        newSubgoal += ","

    rule += newSubgoal

  # --------------------------------------------------------------- #
  #                         EQUATIONS                               #

  # get list of sids for the subgoals of this rule
  cursor.execute( "SELECT eid FROM Equation" ) # get list of eids for this rule
  eqnIDs = cursor.fetchall()
  eqnIDs = tools.toAscii_list( eqnIDs )

  for e in range(0,len(eqnIDs)) :
    currEqnID = eqnIDs[e]
   
    # get associated equation
    if not currEqnID == None :
      cursor.execute( "SELECT eqn FROM Equation WHERE rid == '" + rid + "' AND eid == '" + str(currEqnID) + "'" )
      eqn = cursor.fetchone()
      if not eqn == None :
        eqn = tools.toAscii_str( eqn )

        # convert eqn info to pretty string
        rule += "," + str(eqn)

  # add SndTime eqn (only works for one subgoal time annotation)
  #if not subTimeArg == None and not subTimeArg == "" :
  #  rule += ",SndTime==" + str( subTimeArg )

  # --------------------------------------------------------------- #

  rule += " ;" + "\n" # end all rules with a semicolon

  # .................................. #
  #if goalName == "pre" :
  #  tools.bp( __name__, inspect.stack()[0][3], "rule = " + rule )
  # .................................. #

  return rule


#############################
#  PRIORITIZE NEGATED LAST  #
#############################
def prioritizeNegatedLast( rid, subIDs, cursor ) :

  posSubs = []
  negSubs = []

  # check if subgoal is negated
  # branch on result.
  for subID in subIDs :

    cursor.execute( "SELECT argName FROM SubgoalAddArgs WHERE rid=='" + rid + "' AND sid=='" + subID + "'" )
    sign = cursor.fetchone()

    # positive subgoals may have no argName data
    # all instances of negative subgoals WILL have an argName
    if sign :
      sign = tools.toAscii_str( sign )
    else :
      sign = ""

    if not sign == "notin" :
      posSubs.append( subID )
    else :
      negSubs.append( subID )

  return posSubs + negSubs


#####################
#  PRIORITIZE DOMS  #
#####################
# order domain subgoals first
def prioritizeDoms( rid, subIDs, cursor ) :

  domSubs           = []
  nonDomSubs        = []

  # check if subgoal is a domain subgoal
  # branch on result.
  for subID in subIDs :

    cursor.execute( "SELECT subgoalName FROM Subgoals WHERE rid=='" + rid + "' AND sid=='" + subID + "'" )
    subgoalName = cursor.fetchone()
    subgoalName = tools.toAscii_str( subgoalName )

    if "dom_" in subgoalName[0:4] : 
      domSubs.append( subID )
    else :
      nonDomSubs.append( subID )

  return domSubs + nonDomSubs


################
#  DUMP CLOCK  #
################
# dump and format all clock facts in c4 overlog
def dump_clock( cursor ) :

  if DUMPERS_C4_DEBUG :
    print "...running dumpers_c4 dump_clock..."

  formattedClockFactsList = []

  #cursor.execute( "SELECT * FROM Clock" )
  cursor.execute( "SELECT src, dest, sndTime, delivTime FROM Clock" )
  clockFacts = cursor.fetchall()
  clockFacts = tools.toAscii_multiList( clockFacts )

  if DUMPERS_C4_DEBUG :
    print "dump_clock: clockFacts = " + str(clockFacts)

  for c in clockFacts :
    if DUMPERS_C4_DEBUG :
      print "c = " + str(c)

    clockF = 'clock('
    for i in range(0,len(c)) :
      currData = c[i]
      if i < 2 :
        clockF += '"' + currData + '",'
      else :
        clockF += str(currData)
        if i < len(c)-1 :
          clockF += ","
    clockF += ");" + "\n" # all clock facts end with a semicolon
    formattedClockFactsList.append( clockF )

  return formattedClockFactsList


################
#  DUMP CRASH  #
################
# dump and format all clock facts in c4 overlog
def dump_crash( cursor ) :

  if DUMPERS_C4_DEBUG :
    print "...running dumpers_c4 dump_crash..."

  formattedCrashFactsList = []

  cursor.execute( "SELECT src, dest, sndTime FROM Crash" )
  crashFacts = cursor.fetchall()
  crashFacts = tools.toAscii_multiList( crashFacts )

  if len( crashFacts ) < 1 :
    #tools.bp( __name__, inspect.stack()[0][3], "FATAL ERROR : crash table is empty." )
    cursor.execute( "INSERT INTO Crash (src,dest,sndTime) VALUES ('NULL','NULL','99999999')" )
    cursor.execute( "SELECT src, dest, sndTime FROM Crash" )
    crashFacts = cursor.fetchall()
    crashFacts = tools.toAscii_multiList( crashFacts )
    if DUMPERS_C4_DEBUG :
      print "crashFacts = " + str(crashFacts)

  if DUMPERS_C4_DEBUG :
    print "dump_crash: crashFacts = " + str(crashFacts)

  for c in crashFacts :
    if DUMPERS_C4_DEBUG :
      print "c = " + str(c)

    crashF = 'crash('
    for i in range(0,len(c)) :
      currData = c[i]
      if i < 2 :
        crashF += '"' + currData + '",'
      else :
        crashF += str(currData)
        if i < len(c)-1 :
          crashF += ","
    crashF += ");" + "\n" # all crash facts end with a semicolon
    formattedCrashFactsList.append( crashF )

  return formattedCrashFactsList


#########
#  EOF  #
######### 
