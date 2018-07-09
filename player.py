#! /usr/bin/env python
# -*- coding:utf-8 -*-


import os
import sys
import time
import json
import traceback
import logging
from termcolor import colored
from websocket import create_connection
from importlib import import_module
from deuces import Card
import hashlib
import eventlet
eventlet.monkey_patch()

defaultencoding='utf-8'
if sys.getdefaultencoding()!=defaultencoding:
    reload(sys)
    sys.setdefaultencoding(defaultencoding)

# pip install websocket-client
G_CARD_SPADE = '\x1b[32m\xe2\x99\xa0\x1b[0m'
G_CARD_HEART = '\x1b[31m\xe2\x9d\xa4\x1b[0m'
G_CARD_DIAMOND = '\x1b[31m\xe2\x99\xa6\x1b[0m'
G_CARD_CLUBS = '\x1b[32m\xe2\x99\xa3\x1b[0m'
G_LOG_REPLACE = [
    (G_CARD_SPADE, ' SPADE'),
    (G_CARD_HEART, ' HEART'),
    (G_CARD_DIAMOND, ' DIAMOND'),
    (G_CARD_CLUBS, ' CLUBS'),

]
ws = ""
TIMEOUT = 1.8
G_BASE_DIR = os.path.dirname(os.path.realpath(__file__))
# Configuration for the script
G_CONF = {
    'logging': {
        'format': '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
        'datefmt': '%a, %d %b %Y %H:%M:%S',
        'log_file': os.path.join(G_BASE_DIR, 'player_{version}.log')
    }
}


# Logging module config
logging.basicConfig(
    level=logging.DEBUG,
    format=G_CONF['logging']['format'],
    datefmt=G_CONF['logging']['datefmt'],
    filename=G_CONF['logging']['log_file'].format(version=int(time.time())),
    filemode='w'
)



def mprint(output, log_level=logging.INFO):
    """Generate output to stdout and log file."""
    print(output)
    for item in G_LOG_REPLACE:
        output = output.replace(item[0], item[1])
    logging.log(log_level, output)


class Player(object):
    def __init__(self, name, algModule):
        self.history_list=[]
        self.history_log={}
        self.all_data = {}
        self.all_data['game1'] = {}
        self.game_data = self.all_data['game1']
        self.game_data['round1'] = {}
        self.round_data = self.game_data['round1']
        self.turncount = 1
        self.player = name
        self.alg_module = None
        if algModule != None:
            self.alg_module = import_module(algModule)
        self.basic_info = {}
        self.basic_info['myname'] = name
        self.basic_info['players'] = []
        self.basic_info['cur_players'] = 0
        self.basic_info['cur_action_check'] = 1  #ce-jal, to check whether all previous players take "check" action
        self.basic_info['last_action_diff'] = 1  #ce-jal, means whether self is last one to take action
        self.basic_info['totalbet'] = 0
        self.gamecount=1
        self.roundcount=0
        self.turncount=0
        self.roundname = ''
        self.seatnum = 0
        self.nHand = 0
        self.preRound={}
        self.cardsymbols = {
            'S':colored(u"\u2660".encode('utf-8'), "green"),
            'H':colored(u"\u2764".encode('utf-8'), "red"),
            'D':colored(u"\u2666".encode('utf-8'), "red"),
            'C':colored(u"\u2663".encode('utf-8'), "green")}
        self.boardcards = []
        self.handcards = []
        self.cur_bet=0
        self.cur_round=0
        self.NeedBet=False
        self.eventName=''
        self.round_end_data={}
        pass

    def takeAction(self, action, data, basic_info):
        if action == "__bet":
            return({
                "eventName": "__action",
                "data": {
                    "action": "bet",
                    "amount": 100
                }
            })
        elif action == "__action":
            return({
                "eventName": "__action",
                "data": {
                    "action": "bet",
                    "amount": basic_info['cur_bet']
                }
            })

    def get_cards_string(self, cards):
        allcards = ''
        for card in cards:
            card = str(card)
            newstr = '[' + card[0] + self.cardsymbols[card[1]]
            allcards += newstr
            if card == cards [-1]:
                allcards += ']'
            else:
                allcards += '],'
        return allcards

    def get_format_cards(self, cards):
        allcards = []
        for card in cards:
            card = str(card)
            newcard= Card.new(str(card[0].upper() +card[1].lower()))
            allcards.append(newcard)
        return allcards

    def show_log_msg(self, event, data):
        if event == "__show_action":
            #print "__show_action"
            self.history_list.append(data)
            self.roundcount = data['table']['roundCount']
            self.basic_info['totalbet']=data['table']['totalBet']
            amount = 0
            if self.roundname != data['table']['roundName'] or self.boardcards != data['table']['board']:
                self.roundname = data['table']['roundName']
                self.boardcards = data['table']['board']
                mprint('--- %s --- %s' %(str(data['table']['roundName']),self.get_cards_string(data['table']['board'])))
            if data['action'].has_key('amount'):
                self.cur_bet=data['action']['amount']
                amount = data['action']['amount']
                mprint('%s %ss $%s [Chips: $%s]' %(data['action']['playerName'], str(data['action']['action']), str(data['action']['amount']), str(data['action']['chips'])))
            else:
                self.cur_bet=0
                mprint('%s %ss [Chips: $%s]' %(data['action']['playerName'], str(data['action']['action']), str(data['action']['chips'])))
            if data['action']['action'] not in ('check', 'fold'):
                mprint('action is not check: ' + data['action']['action'])
                self.basic_info['cur_action_check'] = 0 #ce-jal

            if self.basic_info['cur_players']==0:
                self.roundname=data['table']['roundName']
                self.roundcount=data['table']['roundCount']
                self.boardcards=data['table']['board']
                self.basic_info['players']=data['players']
                smallBlind=data['table']['smallBlind']['playerName']
                bigBlind=data['table']['bigBlind']['playerName']
                mprint("smallBlind: "+smallBlind+", bigBlind: "+bigBlind)
                isSmallBlind=False
                self.seatnum=1
                self.basic_info['cur_players']=len(data['players'])
                self.basic_info['cur_playerlist']=[]
                for onePlayer in data['players']:
                    if onePlayer['playerName']==smallBlind:
                        self.round_data[onePlayer['playerName']]={}
                        self.round_data[onePlayer['playerName']]['seat']=0
                        isSmallBlind=True
                    elif onePlayer['playerName']==bigBlind:
                        self.round_data[onePlayer['playerName']]={}
                        self.round_data[onePlayer['playerName']]['seat']=1
                    elif isSmallBlind:
                        self.round_data[onePlayer['playerName']]={}
                        self.seatnum+=1
                        self.round_data[onePlayer['playerName']]['seat']=self.seatnum
                    if onePlayer['isSurvive']==False or onePlayer['folded']==True:
                        self.basic_info['cur_players']-=1
                    else:
                        self.basic_info['cur_playerlist'].append(onePlayer['playerName'])
                    #print onePlayer['playerName'].decode('utf-8')+" seat: "+str(self.round_data[onePlayer['playerName']]['seat'])
                    #print "SuvivedNum: "+str(self.basic_info['cur_players'])
                for onePlayer in data['players']:
                    if onePlayer['playerName']==smallBlind:
                        break
                    if onePlayer['playerName']==bigBlind:
                        continue
                    else:
                        self.round_data[onePlayer['playerName']]={}
                        self.seatnum+=1
                        self.round_data[onePlayer['playerName']]['seat']=self.seatnum
                self.basic_info['cur_seat']=self.round_data[self.player]['seat']
                self.basic_info['last_action_diff'] =  self.basic_info['cur_players'] - self.basic_info['cur_seat'] - 1#ce-jal
            else:
                if data['action']['action']=='fold':
                    if self.round_data[data['action']['playerName']]['seat'] > self.basic_info['cur_seat'] :
                        self.basic_info['last_action_diff'] = self.basic_info['last_action_diff'] - 1 #ce-jal
                        #print 'ttttttt'
                    self.basic_info['cur_players']-=1
                    self.basic_info['cur_playerlist'].remove(data['action']['playerName'])

            player = str(data['action']['playerName'])
            if not self.round_data[player].has_key(self.roundname):
                self.round_data[player][self.roundname] = []
            self.round_data[player][self.roundname].append((str(data['action']['action']), amount, data['action']['chips']))
            #print "_______________________ Show Action Data ________________________"
            #print data
            #print "_______________________ Show Action Data ________________________"
        elif event == "__action":
            #print "__action"
            #print "___________________________________________________________"
            #print data
            #print "___________________________________________________________"
            self.basic_info['cur_bet']=data['self']['minBet']
            mprint("__action: minBet: "+str(self.basic_info['cur_bet']))
            if self.roundname != data['game']['roundName'] or self.boardcards != data['game']['board']:
                self.cur_round+=1
                self.roundname = data['game']['roundName']
                self.boardcards = data['game']['board']
                mprint('--- %s --- %s' %(str(data['game']['roundName']),self.get_cards_string(data['game']['board'])))
            # if data['game']['roundName'] != 'Deal':
                # self.roundname = data['game']['roundName']
                # print '--- %s --- %s' %(str(data['game']['roundName']), self.get_cards_string(self.boardcards))  ##Steven comments
            if str(data['game']['roundName']) == 'Deal' and self.handcards != data['self']['cards']:
                #print '--- %s' %(str(data['game']['roundName']))                     ##Steven comments
                #print '##Round %d' %(self.roundcount)                                ##Steven comments
                self.handcards = data['self']['cards']
                self.round_data['handcards'] = self.get_format_cards(self.handcards)
                mprint(data['self']['playerName'] + ' (me) Hand Card: %s' %(self.get_cards_string(self.handcards)))
            #print "Action: Suvived Num: "+str(self.basic_info['cur_players'])
            self.basic_info['my_clips']=data['self']['chips']
            #print "Action: cur_round: "+str(self.cur_round)                        ###Here have problem
            #print "Action: my_clips: "+str(self.basic_info['my_clips'])
            if self.handcards==[]:
                self.handcards=data['self']['cards']
            if self.basic_info['cur_players']==0:
                self.roundname=data['game']['roundName']
                self.roundcount=data['game']['betCount']
                self.boardcards=data['game']['board']
                self.basic_info['players']=data['game']['players']
                self.basic_info['cur_turn'] = self.roundname
                self.basic_info['board_cards'] = self.get_format_cards(self.boardcards)
                self.basic_info['my_cards'] = self.get_format_cards(self.handcards)
                self.basic_info['cur_round'] = self.cur_round
                smallBlind=data['game']['smallBlind']['playerName']
                bigBlind=data['game']['bigBlind']['playerName']
                mprint("smallBlind: "+smallBlind+", bigBlind: "+bigBlind)
                isSmallBlind=False
                self.seatnum=1
                self.basic_info['cur_players']=len(data['game']['players'])
                self.basic_info['cur_playerlist']=[]
                for onePlayer in data['game']['players']:
                    if onePlayer['playerName']==smallBlind:
                        self.round_data[onePlayer['playerName']]={}
                        self.round_data[onePlayer['playerName']]['seat']=0
                        #self.round_data[onePlayer['playerName']]['plainName']=onePlayer['plainName']
                        isSmallBlind=True
                    elif onePlayer['playerName']==bigBlind:
                        self.round_data[onePlayer['playerName']]={}
                        self.round_data[onePlayer['playerName']]['seat']=1
                        #self.round_data[onePlayer['playerName']]['plainName']=onePlayer['plainName']
                    elif isSmallBlind:
                        self.round_data[onePlayer['playerName']]={}
                        self.seatnum+=1
                        self.round_data[onePlayer['playerName']]['seat']=self.seatnum
                        #self.round_data[onePlayer['playerName']]['plainName']=onePlayer['plainName']
                    if onePlayer['isSurvive']==False or onePlayer['folded']==True:
                        self.basic_info['cur_players']-=1
                    else:
                        self.basic_info['cur_playerlist'].append(onePlayer['playerName'])
                    #print onePlayer['playerName'].decode('utf-8')+" seat: "+str(self.round_data[onePlayer['playerName']]['seat'])
                    mprint("SuvivedNum: "+str(self.basic_info['cur_players']))
                for onePlayer in data['game']['players']:
                    if onePlayer['playerName']==smallBlind:
                        break
                    if onePlayer['playerName']==bigBlind:
                        continue
                    else:
                        self.round_data[onePlayer['playerName']]={}
                        self.seatnum+=1
                        self.round_data[onePlayer['playerName']]['seat']=self.seatnum
                        #self.round_data[onePlayer['playerName']]['plainName']=onePlayer['plainName']
                self.basic_info['cur_seat']=self.round_data[self.player]['seat']
                self.basic_info['last_action_diff'] =  self.basic_info['cur_players'] - self.basic_info['cur_seat'] - 1#ce-jal
        elif event == "__deal" or event == "__bet": #deal is to inform poker comming
            if event == "__deal":
                self.basic_info['cur_action_check'] = 1 #ce-jal
                mprint('Reset current action as check!')

            if event=='__deal' and not self.NeedBet:
                self.boardcards = data['table']['board']
                self.round_data['boardscards'] = self.get_format_cards(self.boardcards)
                if self.roundname != data['table']['roundName'] or self.boardcards != data['table']['board']:
                    self.roundname = data['table']['roundName']
                    self.boardcards = data['table']['board']
                    self.cur_round+=1
                    #print '___deal____'
                    mprint('--- %s --- %s' %(str(data['table']['roundName']), self.get_cards_string(self.boardcards)))  ##Steven comments
                self.NeedBet=False
            elif event=="__bet":
                mprint("__bet: minBet: "+str(self.basic_info['cur_bet']))
                self.boardcards = data['game']['board']
                self.round_data['boardscards'] = self.get_format_cards(self.boardcards)
                if self.roundname != data['game']['roundName'] or self.boardcards != data['game']['board']:
                    self.roundname = data['game']['roundName']
                    self.boardcards = data['game']['board']
                    self.cur_round+=1
                    mprint('--- %s --- %s' %(str(data['game']['roundName']), self.get_cards_string(self.boardcards)))  ##Steven comments
                self.NeedBet=True
        elif event == "__new_round":
            self.history_list.append(data)
            self.cur_round=0
            self.NeedBet=False
            #print "\nnew round"
            #print 'first player %s' %data['players'][0]['playerName']
            self.roundcount = data['table']['roundCount']
            strround = 'round%d' %self.roundcount
            self.game_data[strround] = {}
            self.round_data = self.game_data[strround]
            smallBlind=data['table']['smallBlind']['playerName']
            bigBlind=data['table']['bigBlind']['playerName']
            #print "smallBlind: "+smallBlind+", bigBlind: "+bigBlind
            isSmallBlind=False
            self.seatnum=1
            self.basic_info['cur_players']=len(data['players'])
            self.basic_info['cur_playerlist']=[]
            self.basic_info['cur_action_check'] = 1 #ce-jal
            if self.roundcount == 1:
                self.basic_info['my_clips'] = data['table']['initChips']

            for onePlayer in data['players']:
                if onePlayer['playerName']==smallBlind:
                    self.round_data[onePlayer['playerName']]={}
                    self.round_data[onePlayer['playerName']]['seat']=0
                    #self.round_data[onePlayer['playerName']]['plainName']=onePlayer['plainName']
                    isSmallBlind=True
                elif onePlayer['playerName']==bigBlind:
                    self.round_data[onePlayer['playerName']]={}
                    self.round_data[onePlayer['playerName']]['seat']=1
                    #self.round_data[onePlayer['playerName']]['plainName']=onePlayer['plainName']
                elif isSmallBlind:
                    self.round_data[onePlayer['playerName']]={}
                    self.seatnum+=1
                    self.round_data[onePlayer['playerName']]['seat']=self.seatnum
                    #self.round_data[onePlayer['playerName']]['plainName']=onePlayer['plainName']
                    #print "not Blinds: ", "Name: " ,onePlayer['playerName'], " Seat: " ,self.round_data[onePlayer['playerName']]['seat']
                if onePlayer['isSurvive']==False:
                    self.basic_info['cur_players']-=1
                else:
                    self.basic_info['cur_playerlist'].append(onePlayer['playerName'])
            #print "SuvivedNum: "+str(self.basic_info['cur_players'])
            for onePlayer in data['players']:
                if onePlayer['playerName']==smallBlind:
                    break
                if onePlayer['playerName']==bigBlind:
                    continue
                else:
                    self.round_data[onePlayer['playerName']]={}
                    self.seatnum+=1
                    self.round_data[onePlayer['playerName']]['seat']=self.seatnum
                    #self.round_data[onePlayer['playerName']]['plainName']=onePlayer['plainName']
            self.basic_info['cur_seat']=self.round_data[self.player]['seat']
            self.basic_info['last_action_diff'] =  self.basic_info['cur_players'] - self.basic_info['cur_seat'] - 1#ce-jal
            if self.roundcount!=1:
                mprint("\n")
            mprint("########################## Round" +str(self.roundcount)+ " Start ##########################")
            #print '##Round %d' %(self.roundcount)
            for Player in self.round_data:
                mprint("Player name: %s Seat: %s" % (Player, self.round_data[Player]['seat']))
            mprint("Current Seat: %s, Last action diff: %s" % (self.basic_info['cur_seat'], self.basic_info['last_action_diff'])) #ce-jal
        elif event == "__round_end":
            self.history_list.append(data)
            mprint('----- round end -----')
            #print "_______________________ Round End Data ________________________"
            #print data
            #print "_______________________ Round End Data ________________________"
            self.roundname = ''
            self.handcards = []
            self.basic_info['totalbet'] = 0
            if data.has_key('table'):
                if data['table'].has_key('roundCount'):
                    self.roundcount = data['table']['roundCount']
                else:
                    self.roundcount = self.roundcount + 1
            else:
                self.roundcount = self.roundcount + 1
            #print self.round_data                         ##Steven comments
            #print self.basic_info                         ##Steven comments
            self.history_log[self.roundcount]=self.history_list
            self.history_list=[]
            self.round_end_data['round'+str(self.roundcount)]={}
            #Add for some info
            if self.roundcount==1:
                mprint("self.roundcount %d" %self.roundcount)
                if data.has_key('players'):
                    for onePlayer in data['players']:
                        self.preRound[onePlayer['playerName']]={'chips':onePlayer['chips'],'reloadCount':onePlayer['reloadCount']}
                        winChips=onePlayer['chips']-(onePlayer['reloadCount']+1)*1000
                        self.round_end_data['round'+str(self.roundcount)][onePlayer['playerName']]={'name':onePlayer['playerName'],
                                                                                      'hand_cards':self.get_format_cards(onePlayer['cards']),
                                                                                      'board_cards':self.get_format_cards(data['table']['board']),
                                                                                      'win_one_round':winChips,
                                                                                      'total_win':winChips}
                        if onePlayer['cards'] != []:
                            mprint("@%s HandCards: [%s] BoardCards: [%s] WinChips1Round: $%s TotalWin: $%s" % (onePlayer['playerName'],
                                                                           self.get_cards_string(onePlayer['cards']),
                                                                           self.get_cards_string(data['table']['board']),
                                                                           str(winChips),
                                                                           str(winChips)))
            else:
                if data.has_key('players'):
                    for onePlayer in data['players']:
                        preChips=0
                        preReloadCount=0
                        if self.preRound.has_key(onePlayer['playerName']):
                            preChips=self.preRound[onePlayer['playerName']]['chips']
                            preReloadCount=self.preRound[onePlayer['playerName']]['reloadCount']+1
                        winChips=onePlayer['chips']-preChips-(onePlayer['reloadCount']+1-preReloadCount)*1000
                        totalWin=onePlayer['chips']-(onePlayer['reloadCount']+1)*1000
                        self.preRound[onePlayer['playerName']]={'chips':onePlayer['chips'],'reloadCount':onePlayer['reloadCount']}
                        self.round_end_data['round'+str(self.roundcount)][onePlayer['playerName']]={'name':onePlayer['playerName'],
                                                                                      'hand_cards':self.get_format_cards(onePlayer['cards']),
                                                                                      'board_cards':self.get_format_cards(data['table']['board']),
                                                                                      'win_one_round':winChips,
                                                                                      'total_win':totalWin}
                        if onePlayer['cards'] != []:
                            mprint("@%s HandCards: [%s] BoardCards: [%s] WinChips1Round: $%s TotalWin: $%s" % (onePlayer['playerName'],
                                                                                     self.get_cards_string(onePlayer['cards']),
                                                                                     self.get_cards_string(data['table']['board']),
                                                                                     str(winChips),
                                                                                     str(totalWin)))
            mprint("########################## Round" +str(self.roundcount)+ " End ##########################")

        elif event == "__game_over":
            mprint('----- game over -----')
            mprint("_______________________ Game Over Data ________________________")
            mprint("Winner:")
            for onePlayer in data['winners']:
                mprint("win_player@%s Rank: %s Chips: $%s Cards: [%s]" % (onePlayer['playerName'],
                                                                         str(onePlayer['hand']['rank']),
                                                                         str(onePlayer['chips']),
                                                                         self.get_cards_string(onePlayer['hand']['cards'])))
            mprint("Loser: ")
            for onePlayer in data['players']:
                if onePlayer['chips']==0:
                    mprint("@"+onePlayer['playerName'])
            mprint("########################## Game " +str(self.gamecount)+ "Over ##########################")
        if event == "__bet":
            mprint("_real_bet: minBet: "+str(data['self']['minBet']))
            self.basic_info['cur_bet']=0 #data['self']['minBet']
            #print "Action: minBet: "+str(self.basic_info['cur_bet'])
            if self.roundname != data['game']['roundName'] or self.boardcards != data['game']['board']:
                self.cur_round+=1
                self.roundname = data['game']['roundName']
                self.boardcards = data['game']['board']
                mprint('--- bet %s --- %s' %(str(data['game']['roundName']), self.get_cards_string(self.boardcards)))  ##Steven comments
            if str(data['game']['roundName']) == 'Deal':
                mprint('--- %s' %(str(data['game']['roundName'])))                    ##Steven comments
                mprint('##Round %d' %(self.roundcount))                                ##Steven comments
                self.handcards = data['self']['cards']
                self.round_data['handcards'] = self.get_format_cards(self.handcards)
                mprint('Hand Card: %s' %(self.get_cards_string(self.handcards)))
            #print "Action: Suvived Num: "+str(self.basic_info['cur_players'])
            self.basic_info['my_clips']=data['self']['chips']
            #print "Action: cur_round: "+str(self.cur_round)
            #print "Action: my_clips: "+str(self.basic_info['my_clips'])
        if event in ("__bet", "__action"):
            self.basic_info['small_blind'] = data['game']['smallBlind']['amount']
            self.basic_info['big_blind'] = data['game']['bigBlind']['amount']
            self.basic_info['players'] = data['game']['players']
            #import pdb
            #pdb.set_trace()
            self.basic_info['round_bet'] = data['self']['bet']

        self.basic_info['total_round'] = self.roundcount
        self.basic_info['cur_turn'] = self.roundname
        self.basic_info['board_cards'] = self.get_format_cards(self.boardcards)
        self.basic_info['my_cards'] = self.get_format_cards(self.handcards)
        self.basic_info['cur_round'] = self.cur_round

    def DefaultAction(self):
        return {
        "eventName" : "__action",
        "data" : {
        "action" : "fold"
        }}

    def doListen(self):
        try:
            global ws,IsSetAction,TIMEOUT
            #ws = create_connection("ws://10.64.8.16")
            ws = create_connection("ws://pokerai.trendmicro.com.cn")
            #ws = create_connection("ws://116.62.203.120")
            ws.send(json.dumps({
                "eventName": "__join",
                "data": {
                    "playerName": self.player
                }
            }))
            date_md5 = hashlib.md5(self.player).hexdigest()
            self.player = date_md5
            nRound = 0
            nHand = 0
            while 1:
                result = ws.recv()
                msg = json.loads(result)
                event_name = msg["eventName"]
                data = msg["data"]
                #print 'Event: %s' %event_name
                self.show_log_msg(event_name, data)
                #print data
                if event_name=="__game_over":
                    self.gamecount += 1
                    ws.close()
                    break
                elif event_name=='__round_end':
                    if self.alg_module and 'roundEnd' in dir(self.alg_module):
                        self.alg_module.roundEnd(self.round_end_data['round'+str(self.roundcount)])
                else:
                    if event_name in ["__bet", "__action", "__start_reload"]:
                        IsSetAction=False
                        self.eventName=event_name
                        if self.alg_module:
                            try:
                                with eventlet.Timeout(TIMEOUT):
                                    decision=self.alg_module.takeAction(self.eventName,self.game_data,self.basic_info)
                            except eventlet.Timeout as e:
                                mprint("Timeout")
                                mprint(e)
                                decision=self.DefaultAction()
                            #decision = self.alg_module.takeAction(self.eventName, self.game_data, self.basic_info)
                        else:
                            decision = self.takeAction(self.eventName, self.game_data, self.basic_info)
                        ws.send(json.dumps(decision))
        except Exception as e:
            mprint(e)
            mprint('Exception traceback: %s' %traceback.format_exc())
            #doListen()

if __name__ == '__main__':
    strPlayer = sys.argv[1]
    strAlgModule = "alg_CEJal"
    #if len(sys.argv) > 2:
    #    strAlgModule = sys.argv[2]
    plyr = Player(strPlayer, strAlgModule)
    plyr.doListen()
