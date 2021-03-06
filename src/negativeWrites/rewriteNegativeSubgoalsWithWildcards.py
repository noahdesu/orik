#/usr/bin/env python

'''
rewriteNegativeSubgoalsWithWildcards.py
'''

import inspect, os, string, sys
import sympy

# ------------------------------------------------------ #
# import sibling packages HERE!!!
if not os.path.abspath( __file__ + "/../.." ) in sys.path :
  sys.path.append( os.path.abspath( __file__ + "/../.." ) )

if not os.path.abspath( __file__ + "/../../dedt/translators" ) in sys.path :
  sys.path.append( os.path.abspath( __file__ + "/../../dedt/translators" ) )

from dedt        import Rule
from evaluators  import c4_evaluator
from translators import c4_translator
from utils       import clockTools, tools, dumpers

# ------------------------------------------------------ #

#############
#  GLOBALS  #
#############
NEGATIVEWRITES_DEBUG = tools.getConfig( "DEDT", "NEGATIVEWRITES_DEBUG", bool )

arithOps = [ "+", "-", "*", "/" ]


##############################################
#  REWRITE NEGATIVE SUBGOALS WITH WILDCARDS  #
##############################################
def rewriteNegativeSubgoalsWithWildcards( cursor ) :

  newRuleMeta = []

  # ------------------------------------------- #
  # get all rids
  cursor.execute( "SELECT rid FROM RUlE" )
  rids = cursor.fetchall()
  rids = tools.toAscii_list( rids )

  for rid in rids :
    cursor.execute( "SELECT sid FROM Subgoals WHERE rid=='" + rid + "'" )
    sids = cursor.fetchall()
    sids = tools.toAscii_list( sids )

    # ------------------------------------------- #
    # examine all subgoals per rule
    for sid in sids :

      cursor.execute( "SELECT argName FROM SubgoalAddArgs WHERE rid=='" + rid + "' AND sid=='" + sid + "'" )
      sign = cursor.fetchone()
      if sign :
        sign = tools.toAscii_str( sign )
      else :
        sign = ""

      if sign == "notin" :
        cursor.execute( "SELECT attID,attName,attType FROM SubgoalAtt WHERE rid=='" + rid + "' AND sid=='" + sid + "'" )
        attData = cursor.fetchall()
        attData = tools.toAscii_multiList( attData )

        # ------------------------------------------- #
        # examine all atts per subgoal per rule
        for att in attData :
          attID   = att[0]
          attName = att[1]
          attType = att[2]

          if attName == "_" :
            newRule = rewriteRule( rid, sid, attData, cursor )
            newRuleMeta.append( newRule )
            break

      else :
        continue

  return newRuleMeta


##################
#  REWRITE RULE  #
##################
# attData contains the full att list for the input (original) subgoal
def rewriteRule( rid, sid, attData, cursor ) :

  print "#################################################################"
  print " ... running REWRITE RULE from rewriteSubgoalsWithWildcards ... #"
  print "#################################################################"

  print "BEFORE : attData : " + str( attData )

  # ------------------------------------------- #
  # get name of sid
  cursor.execute( "SELECT subgoalName FROM Subgoals WHERE rid=='" + rid + "' AND sid=='" + sid + "'" )
  subgoalName = cursor.fetchone()
  subgoalName = tools.toAscii_str( subgoalName )

  # ------------------------------------------- #
  # branch on idb subgoals.
  # if negated subgoal with wildcard is IDB, then ensure all attTypes are defined
  # by pulling attTypes from the IDB goal attribute list.

  if not tools.isFact_only( subgoalName, cursor ) :
    # get rule id for the idb
    cursor.execute( "SELECT rid FROM Rule WHERE goalName=='" + subgoalName + "'" )
    idbrid = cursor.fetchone()
    idbrid = tools.toAscii_str( idbrid )

    # get goal schema
    cursor.execute( "SELECT attID,attName,attType FROM GoalAtt WHERE rid=='" + idbrid + "'" )
    idbAttData = cursor.fetchall()
    idbAttData = tools.toAscii_multiList( idbAttData )

    print "idbAttData : " + str( idbAttData )

    # fix original subgoal att list types
    tmp = []
    for i in range(0,len(idbAttData)) :
      idb_att  = idbAttData[i]
      orig_att = attData[i]

      attID   = orig_att[0]
      attName = orig_att[1]
      attType = idb_att[2]

      tmp.append( [ attID, attName, attType ] )
    attData = tmp

  # ------------------------------------------- #
  # generate new subgoal name
  newSubgoalName = subgoalName + "_" + tools.getID_4() + "_wildcardrewrite"

  # ------------------------------------------- #
  # generate new subgoal att list
  attNameList = [ ]
  newSubgoalAttList = [ ]
  attID = 0
  for att in attData :
    attName = att[1]
    attType = att[2]

    if not attName == "_" and attName not in attNameList :
      newSubgoalAttList.append( [ attID, attName, attType ] )
      attNameList.append( attName )
      attID += 1

  if True :
    print ">> ORIG RULE <<"
    print dumpers.reconstructRule( rid, cursor )
    print ">>>         <<<"
    print "subgoalName       = " + subgoalName
    print "newSubgoalName    = " + newSubgoalName
    print "attData           = " + str( attData )
    print "newSubgoalAttList = " + str( newSubgoalAttList )

  # ------------------------------------------- #
  # update subgoal name
  cursor.execute( "UPDATE Subgoals SET subgoalName=='" + newSubgoalName + "' WHERE rid=='" + rid + "' AND sid=='" + sid + "'" )

  # ------------------------------------------- #
  # delete old subgoal att data
  arity = len( attData )
  for attID in range( 0, arity ) :
    cursor.execute( "DELETE FROM SubgoalAtt WHERE rid=='" + rid + "' AND sid=='" + sid + "' AND attID=='" + str( attID ) + "'"  )

  # ------------------------------------------- #
  # input new subgoal att data
  for att in newSubgoalAttList :
    attID   = att[0]
    attName = att[1]
    attType = att[2]

    cursor.execute( "INSERT INTO SubgoalAtt VALUES ('" + rid + "','" + sid + "'," + str(attID) + ",'" + attName + "','" + attType + "')" )

  # ------------------------------------------- #
  # add new rule

  print "-------------------------------------"
  print "subgoalName       : " + subgoalName
  print "newSubgoalName    : " + newSubgoalName
  print "attData           : " + str( attData )
  print "newSubgoalAttList : " + str( newSubgoalAttList )
  #tools.bp( __name__, inspect.stack()[0][3], "asdf" )

  newRule = addNewRule( subgoalName, newSubgoalName, attData, newSubgoalAttList, cursor )

  return newRule

##################
#  ADD NEW RULE  #
##################
def addNewRule( origSubgoalName, newSubgoalName, origSubgoalAttList, newSubgoalAttList, cursor ) :

  print "////////////////////////////////////////////"
  print "origSubgoalName    : " + origSubgoalName
  print "newSubgoalName     : " + newSubgoalName
  print "origSubgoalAttList : " + str( origSubgoalAttList )
  print "newSubgoalAttList  : " + str( newSubgoalAttList )

  # ------------------------------------------- #
  # generate new rule id
  newRID = tools.getID()

  # ------------------------------------------- #
  # save goal data
  goalTimeArg   = ""
  rewrittenFlag = True

  # insert into Rule
  cursor.execute("INSERT INTO Rule (rid, goalName, goalTimeArg, rewritten) VALUES ('" + newRID + "','" + newSubgoalName + "','" + goalTimeArg + "','" + str(rewrittenFlag) + "')")

  # insert into GoalAtt
  for att in newSubgoalAttList :
    attID   = att[0]
    attName = att[1]
    attType = att[2]

    cursor.execute("INSERT INTO GoalAtt VALUES ('" + newRID + "','" + str(attID) + "','" + attName + "','" + attType + "')")

  # ------------------------------------------- #
  # generate new subgoal id
  subgoalID      = tools.getID()
  subgoalTimeArg = ""

  # insert into Subgoals
  cursor.execute( "INSERT INTO Subgoals VALUES ('" + newRID + "','" + subgoalID + "','" + origSubgoalName + "','" + subgoalTimeArg + "')" )

  # insert into SubgoalAtt
  for att in origSubgoalAttList :
    attID   = att[0]
    attName = att[1]
    attType = att[2]

    cursor.execute( "INSERT INTO SubgoalAtt VALUES ('" + newRID + "','" + subgoalID + "','" + str(attID) + "','" + attName + "','" + attType + "')" )

  # ------------------------------------------- #
  # generate meta for new rule
  newRule = Rule.Rule( newRID, cursor )

  return newRule


#########
#  EOF  #
#########
