#! /usr/bin/env python
# -*- coding:utf-8 -*-


import time
import json
import sys
import traceback
import random
from termcolor import colored
#from websocket import create_connection
from importlib import import_module
from evaluepoker import EvaluePoker
from deuces import Card
import datetime

class DavidAction():
    def __init__ (self,action,data,basic_info):
        self.action = action
        self.data = data
        self.basic_info = basic_info
        self.myname = ''
        self.mychips = 0
        self.currentbet = 1
        self.myseat = 0
        self.mycards = []
        self.boardcards = []
        self.stage = ''
        self.players_count = 0
        self.playercount = 0
        self.cur_round = 0
        self.cur_round_action = ''
        self.prob = 0
        dsymbols = {
            'S':colored(u"\u2660".encode("utf-8", 'ignore'),"green"),
            'H':colored(u"\u2764".encode("utf-8", 'ignore'), "red"),
            'D':colored(u"\u2666".encode("utf-8", 'ignore'), "red"),
            'C':colored(u"\u2663".encode("utf-8", 'ignore'),"green")
        }

        #Tuning the radio
        self.total_chips = 1000
        self.allin_pro = 0.6
        self.bet_radio = 0.5
        self.non_deal_range = 0.6
        self.deal_range = 4
        self.check_other_bet_radio = 0.05
        self.check_smallchip_radio = 0.2
        self.check_smallbet_radio = 0.2

    def CheckIfSmallChip(self, chip_count):
        if(chip_count > (self.check_smallchip_radio * self.mychips)):
            return False
        #小注
        return True

    def CheckIfSmallBet(self, bet_count):
        count = int(self.mychips/self.currentbet)
        if(bet_count> (count*self.check_smallbet_radio*self.currentbet)):
            return False
        #小的加注
        return True

    def CheckOtherPlayer(self):
        check_count = 0
        small_call_count = 0
        large_call_count = 0
        small_bet_count = 0
        large_bet_count = 0

        cur_round_str = 'round%s'%self.cur_round
        print colored("current round","yellow"), cur_round_str
        if(not self.data.has_key(cur_round_str)):
            return False
        round_info = self.data[cur_round_str]

        for key in round_info:
            play_info = round_info[key]
            print "key       = ", key,"\n", "play_info = ", play_info
            if 'seat' in play_info:
                if(play_info['seat'] < self.myseat and self.stage in play_info):
                    action_info = play_info[self.stage][-1]
                    action_name = action_info[0]
                    bet_count =  action_info[1]
                    rest_clips =   action_info[2]
                    if(action_name ==  'check'):
                        check_count +=1
                    if(action_name == 'call' ):
                        if(self.CheckIfSmallChip(bet_count)):
                            small_call_count +=1
                        else:
                            large_call_count +=1
                    if(action_name == 'bet' ):
                        if(self.CheckIfSmallBet(bet_count)):
                            small_bet_count +=1
                        else:
                            large_bet_count +=1
                    if(action_name == 'raise' ):
                        large_bet_count += 1
        print "large_call_count = ", large_call_count, "large_bet_count = ", large_bet_count
        if(large_call_count >=2 or large_bet_count >=2 or (large_call_count+large_bet_count)>=2):
            return False
        else:
            return True

    def MyEvaCard(self):
        if(self.stage == 'Deal' or len(self.boardcards) ==0):
            eva = EvaluePoker()
            prob = eva.handle_hold_rank(self.mycards)
            self.prob = prob
        else:
            eva = EvaluePoker()
            prob = eva.handle_stage_rank(self.stage.lower(),self.playercount,self.mycards, self.boardcards )
            self.prob = prob
        #print "self.prob = ", self.prob
        return True

    def get_cards_string(self, cards):
        allcards = ''
        for card in cards:
            card = str(card)
            if card[0] == 'T':
                newstr = '[10' + self.cardsymbols[card[1]] + '], '
            else:
                newstr = '[' + card[0] + self.cardsymbols[card[1]] + '], '
            allcards += newstr
        return allcards

    def handle_deal_stage(self):
        eva = EvaluePoker()
        rank = eva.handle_hold_rank(self.mycards)
        basic_info = self.basic_info

        action = 'call'
        amount = basic_info['big_blind']

        print 'My poke Rank: ', rank , " Currnt bet", basic_info['cur_bet'], " Currnt BB: ", basic_info['big_blind'], "my current chips: ", basic_info['my_clips']
        sys.stdout.flush()

        if rank == 1 and basic_info['cur_players'] <=5:
            action = 'bet'
            if basic_info['round_bet'] <= basic_info['my_clips']:
                amount = basic_info['round_bet']
            elif basic_info['my_clips']>=200 and basic_info['big_blind']<= basic_info['my_clips']:
                amount = 200;
            else:
                amount = basic_info['my_clips']
        elif rank == 1 and basic_info['cur_players'] >5:
            if basic_info['cur_bet'] <=200 and basic_info['my_clips']>=200:
                action = 'call'
            else:
                action = 'fold'
                amount = 0

        if rank ==2 or rank == 3 or rank == 4:
            if  basic_info['cur_bet'] <=2*basic_info['big_blind'] and basic_info['cur_players'] <=10:
                action = 'call'
            elif basic_info['cur_bet'] <=3*basic_info['big_blind'] and basic_info['cur_players'] <=5:
                action = 'call'
            elif basic_info['cur_bet'] <=4.5*basic_info['big_blind'] and basic_info['cur_players'] <=3:
                action = 'call'
            else:
                action = 'fold'
                amount = 0

        if rank == 5 or rank == 6:
            if  basic_info['cur_bet'] <=2*basic_info['big_blind'] and basic_info['cur_players'] <=8 and basic_info['big_blind']<= 640:
                action = 'call'
            elif basic_info['cur_bet'] <=2*(basic_info['big_blind']+basic_info['small_blind']) and basic_info['cur_players'] <=3  and basic_info['big_blind']<=1280:
                action = 'call'
            else:
                action = 'fold'
                amount = 0

        

        if rank == 7 or rank ==8:
            if  basic_info['cur_bet'] <=(basic_info['big_blind']+basic_info['small_blind']) and basic_info['cur_players'] <=6 and basic_info['big_blind']<=320:
                action = 'call'
            else:
                action = 'fold'
                amount = 0

        if rank ==9:
            if  basic_info['cur_bet'] <=basic_info['big_blind'] and basic_info['cur_players'] <=4 and basic_info['totalbet']<=(basic_info['cur_players']-1)*basic_info['big_blind'] and basic_info['big_blind']<=320:
                print "***************Current totalbet =", basic_info['totalbet']
                action = 'call'
            else:
                action = 'fold'
                amount = 0
        if action == 'fold' and self.currentbet == 0: #when in big blind pos, will fold in many case, here currentbet equals minBet
            print 'Reset fold to check for current bet is zero'
            action = 'check'  
        return action, amount

    def handle_flop_stage(self):
        basic_info = self.basic_info
        eva = EvaluePoker()
        #print "time = ", datetime.datetime.now()
        self.prob = 0
        self.prob = eva.handle_stage_rank('flop', basic_info['cur_players'], basic_info['my_cards'], basic_info['board_cards'])
        #print "time = ", datetime.datetime.now()
        
        action, amount = self.EvaluateAction()
        print "RequestAction ", self.action, "MyProb:", self.prob , " MyAction:", action, " Amount:", amount, " Current min bet:", basic_info['cur_bet']," Currnt BB:", basic_info['big_blind'], " MyChips:", basic_info['my_clips']
        return action, amount

    def handle_turn_stage(self):
        basic_info = self.basic_info
        eva = EvaluePoker()
        self.prob = 0
        self.prob = eva.handle_stage_rank('turn', basic_info['cur_players'], basic_info['my_cards'], basic_info['board_cards'])

        action, amount = self.EvaluateAction()
        print "RequestAction ", self.action, "MyProb:", self.prob , " MyAction:", action, " Amount:", amount, " Current min bet:", basic_info['cur_bet']," Currnt BB:", basic_info['big_blind'], " MyChips:", basic_info['my_clips']
        return action, amount

    def handle_river_stage(self):
        basic_info = self.basic_info
        eva = EvaluePoker()
        self.prob = 0
        self.prob = eva.handle_stage_rank('river', basic_info['cur_players'], basic_info['my_cards'], basic_info['board_cards'])

        action, amount = self.EvaluateAction()
        print "RequestAction ", self.action, "MyProb:", self.prob , " MyAction:", action, " Amount:", amount, " Current min bet:", basic_info['cur_bet']," Currnt BB:", basic_info['big_blind'], " MyChips:", basic_info['my_clips']
        return action, amount

    def EvaluateAction(self):
        if(self.action == "__bet" or self.action == "__action"):
            if self.currentbet == 0:
                #ce-jal if it's the last one to take action, be aggressive
                if self.basic_info['last_action_diff'] <= 0 and  self.basic_info['cur_action_check'] == 1:
                    print "Use last_action_diff index to take aciton!"
                    big_blind = self.basic_info['big_blind']
                    mod1 = self.mychips / big_blind
                    action = "bet"
                    amount = 0
                    if self.prob >= 0.5 and mod1 >=2 :
                        amount = big_blind*mod1/2 
                    elif self.prob >= 0.3 and mod1 > 4:
                        amount =  big_blind*2 
                    elif self.prob >= 0.2 and mod1 >=2 :
                        amount = big_blind
                    if amount > 0 : 
                        print "Nobody bet, I bet!"  
                        return action, amount
    
                return "check",0

            
            if(self.prob > 0.92):
                max_bet_mod1 = self.mychips / self.currentbet
                pro_max_bet_mod1 = int(max_bet_mod1 * self.bet_radio)
                print ">0.92 max_bet_mod1 = ",max_bet_mod1, " self.currentbet = ",self.currentbet
                if(pro_max_bet_mod1>1):
                    max_bet_count =  random.randint(pro_max_bet_mod1, max_bet_mod1)  * self.currentbet
                else:
                    max_bet_count =  self.currentbet
                return "bet", max_bet_count
            if(self.prob > 0.7):
                max_bet_mod1 = self.mychips / self.currentbet
                pro_max_bet_mod1 = int(max_bet_mod1 * self.bet_radio)
                print ">0.7 max_bet_mod1 = ",max_bet_mod1, " self.currentbet = ",self.currentbet
                if(pro_max_bet_mod1>1):
                    max_bet_count =  random.randint(int(pro_max_bet_mod1/3), int(max_bet_mod1/1.5))  * self.currentbet
                else:
                    max_bet_count =  self.currentbet
                return "bet", max_bet_count
            if(self.prob <= 0.7 and self.prob >= 0.3):
                if(self.prob >= self.non_deal_range):
                    max_bet_mod1 = self.mychips/ self.currentbet
                    pro_max_bet_mod1 = int(max_bet_mod1 * self.bet_radio)
                    print "0.3-0.7 max_bet_mod1 = ",max_bet_mod1, " self.currentbet = ",self.currentbet
                    if(pro_max_bet_mod1>1):
                        max_bet_count =  random.randint(int(pro_max_bet_mod1/4), int(pro_max_bet_mod1/2))  * self.currentbet
                    else:
                        max_bet_count =  self.currentbet
                    return "bet", max_bet_count
                else:
                    if self.CheckOtherPlayer():
                        return "call",0
                    else:
                        return "fold",0
            if(self.prob>=0.2 and self.prob <0.3):
                if self.basic_info['cur_turn'] == "Flop":
                    num = 3
                elif self.basic_info['cur_turn'] == "Turn":
                    num = 5
                else:
                    num = 7
                print "self.playercount = ",self.playercount, "num = ", num, "************self.basic_info['totalbet'] = ", self.basic_info['totalbet']
                if self.playercount <= 3 and self.basic_info['totalbet'] <= (num*self.basic_info['big_blind']) and self.basic_info['big_blind']<=320:
                    return "call",0
                else:
                    return "fold",0
            if(self.prob<0.2):
                print "************self.basic_info['totalbet'] = ", self.basic_info['totalbet']
                if self.playercount <= 2 and self.basic_info['totalbet'] <= (4*self.basic_info['big_blind']) and self.basic_info['big_blind']<=160:
                    return "call",0
                else:
                    return "fold",0

    def getBasicInfos(self):
        self.myname      = self.basic_info['myname']
        self.mychips     = self.basic_info['my_clips']
        self.currentbet  = self.basic_info['cur_bet']
        self.myseat      = self.basic_info['cur_seat']
        self.stage       = self.basic_info['cur_turn']
        self.cur_round   = self.basic_info['total_round']
        self.playercount = self.basic_info['cur_players']
        self.mycards     = self.basic_info['my_cards']
        self.boardcards  = self.basic_info['board_cards']

        #print "myname          = ",self.myname
        #print "mychips         = ",self.mychips
        #print "self.currentbet = ",self.currentbet
        #print "self.myseat     = ",self.myseat
        #print "self.stage      = ",self.stage
        #print "self.cur_round  = ",self.cur_round
        #print "self.playercount= ",self.playercount
        #print "self.mycards    = ",self.mycards
        #print "self.boardcards = ",self.boardcards  #self.get_cards_string(self.boardcards)
        #sys.stdout.flush()

        if (self.myname == '') or (self.mychips == '') or (self.myname == '') or (self.currentbet == '') or (self.myseat == '') or (self.stage == '') or (self.cur_round == '') or (self.playercount == '') or (self.mycards == ''):
            return 0
        else:
            return 1

    def PlayPoker(self):
        try:
            if self.action == "__start_reload":
                return({
                    "eventName": "__reload"
                    })

            if (self.action == "__bet") or (self.action == "__action"):
                if self.stage == 'Deal':
                    #print "Deal =============>> ",datetime.datetime.now()
                    action, amount = self.handle_deal_stage()
                elif self.stage == 'Flop':
                    #print "Flop =============>> ",datetime.datetime.now()
                    action, amount = self.handle_flop_stage()
                elif self.stage == 'Turn':
                    #print "Turn =============>> ",datetime.datetime.now()
                    action, amount = self.handle_turn_stage()
                elif self.stage == 'River':
                    #print "River ============>> ",datetime.datetime.now()
                    action, amount = self.handle_river_stage()
                if action == 'fold' and self.basic_info['cur_action_check'] == 1 : 
                    action = 'check'
                    print '####ce-jal: make fold as check'
                    
                #print "Action complete <<== ",datetime.datetime.now(), 'action = ',action, " amount = ",amount
                if action == 'bet':
                    return({"eventName": "__action", "data": {"action": action,    "amount": amount}})
                else:
                    return({"eventName": "__action", "data": {"action": action}})

        except Exception, e:
            print "Exception : ",e
            if(self.action == "__action"):
                return({
                        "eventName": "__action",
                        "data": {
                            "action": "fold",
                            }
                        })
            elif (self.action == "__bet"):
                return({
                        "eventName": "__action",
                        "data": {
                            "action": "call",
                            }
                        })
            elif self.action == "__start_reload":
                return({
                    "eventName": "__reload"
                    })


def takeAction(action, data, basic_info):
    #Analyze my cards
    handle = DavidAction(action, data, basic_info)
    result = handle.getBasicInfos()
    ret = handle.PlayPoker()
    return ret
