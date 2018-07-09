from deuces import Card
from deuces import Evaluator
from deuces import Deck
import random



TWO_CARD_RANK_EVA = {'1': [[14, 14], [13, 13], [12, 12], [11, 11], [14, 13, 's']],
                     '2': [[14, 13], [14, 12, 's'], [14, 11, 's'], [13, 12, 's'], [10, 10]],
                     '3': [[14, 12], [14, 10, 's'], [13, 11, 's'], [12, 11, 's'], [11, 10, 's'], [9, 9]],
                     '4': [[14, 11], [13, 13], [13, 10, 's'], [12, 10, 's'], [11, 9, 's'], [9, 8, 's'], [8, 8]],
                     '5': [[14, 9, 's'], [14, 8, 's'], [14, 7, 's'], [14, 6, 's'], [14, 5, 's'], [14, 4, 's'],
                          [14, 3, 's'], [14, 2, 's'], [13, 11], [12, 11], [11, 10], [11, 19, 's'], [10, 8, 's'],
                          [9, 7, 's'], [8, 7, 's'], [7, 7], [7, 6, 's'], [6, 6]],
                     '6': [[14, 10], [13, 10], [12, 10], [11, 8, 's'], [8, 6, 's'], [7, 5, 's'], [6, 5, 's'],
                          [5, 5], [5, 4, 's']],
                     '7': [[13, 9, 's'], [13, 8, 's'], [13, 7, 's'], [13, 6, 's'], [13, 5, 's'], [13, 4, 's'],
                          [13, 3, 's'], [13, 2, 's'], [11, 9], [10, 9], [9, 8], [6, 4, 's'], [5, 3, 's'],
                          [4, 4], [4, 3, 's'], [3, 3], [2, 2]],
                     '8': [[14, 9], [13, 9], [12, 9], [11,8], [11, 7, 's'], [10, 8], [9, 6, 's'], [8, 7],
                          [8, 5, 's'], [7, 6], [7, 4, 's'], [6, 5], [5, 4], [4, 2, 's'], [3, 2, 's']]
                    }

class RemovableDeck(Deck):
    """
    Class representing a deck. The first time we create, we seed the static
    deck with the list of unique card integers. Each object instantiated simply
    makes a copy of this object and shuffles it.
    """

    def __init__(self):
        Deck.__init__(self)

    def remove(self, cards):
        for card in cards:
            self.cards.remove(card)

    def shuffle_without_reset(self):
        shuffle(self.cards)

class EvaluePoker:
    #This function will return victory rate about the hand 
    def handle_hold_rank(self,hand):
        card_1 = Card.get_rank_int(hand[0]) + 2
        card_2 = Card.get_rank_int(hand[1]) + 2

        if card_1 > card_2:
            fst_card = card_1
            sec_card = card_2
        else:
            fst_card = card_2
            sec_card = card_1
        
        card_list = [fst_card, sec_card]
        if Card.get_suit_int(hand[0]) == Card.get_suit_int(hand[1]):
            card_list.append('s')
        
        rank = 9
        for key in TWO_CARD_RANK_EVA.keys():
            value = TWO_CARD_RANK_EVA[key]
            if card_list in value:
                rank = int(key)
                break
        
        return rank
    
    
    def handle_stage_rank_new(self, stage, players, hand_cards, board_cards = []):
        
        if hand_cards is None or len(hand_cards) != 2:
            #logging.error("hand_cards error: %s", hand_cards)
            print "hand_cards error: " , hand_cards
            return 0
        if board_cards is None:
            board_cards = []
        if players >= 12 or players < 0:
            #logging.warning("players too much or too few: %d, change it to 1", players)
            print "players too much or too few: %d, change it to 1" %  players
            players = 1

        board = board_cards
        hand = hand_cards
        win = 0
        succeeded_sample = 0
        evaluator = Evaluator()
        deck = RemovableDeck()
        deck.remove(hand)
        deck.remove(board)

        for i in range(10000):
            new_deck = copy.deepcopy(deck)
            new_deck.shuffle_without_reset()
            board_cards_to_draw = 5 - len(board)
            board_sample = board 
            if board_cards_to_draw > 0:
                board_sample +=  new_deck.draw(board_cards_to_draw)

            try:
                my_rank = evaluator.evaluate(board_sample, hand)
                i_can_succeed = True
                for j in range(players):
                    hand_sample = new_deck.draw(2)
                    other_rank = evaluator.evaluate(board_sample, hand_sample)
                    if other_rank < my_rank:
                        i_can_succeed = False
                        break
            except Exception, e:
                continue

            if i_can_succeed:
                win += 1
            succeeded_sample += 1

        win_prob = win/float(succeeded_sample)
        return win_prob
    
    def handle_stage_rank(self, stage, play_num, hand, board = []):
        evaluator = Evaluator()
        cur_set = []
        if play_num < 2 or hand == []:
            print 'play number or hands error, please check'
            return -1
            
        cur_set.extend(hand)
        cur_set.extend(board)

        v_sum = 0
        l_sum = 0
        
        max_prob = 0
        
        draw_num = play_num * 2
        if stage == 'flop':
            draw_num += 2
        elif stage == 'turn':
            draw_num += 1        
        
        for t in range(4):
            v_sum = 0
            l_sum = 0
            for i in range(5000):
                c_board = []
                c_board.extend(board)
                deck = Deck()
                cards = deck.draw(draw_num)
                exist = 0
                for one_card in cards:
                    if one_card in cur_set:
                        exist = 1
                        break

                if exist == 1:
                    continue

                # last one/two append in board
                if stage == 'flop':
                    c_board.append(cards[-1])
                    c_board.append(cards[-2])                
                elif stage == 'turn':
                    c_board.append(cards[-1])
                    
                rank_score = evaluator.evaluate(c_board, hand)
                
                victory = 1
                for play_one in range(play_num):
                    simu_hand = [cards[play_one*2], cards[play_one*2+1]]                
                    p1_score = evaluator.evaluate(c_board, simu_hand)
                    if p1_score < rank_score:
                        victory = 0
                        break
                
                if victory == 1:
                    v_sum += 1
                else:
                    l_sum += 1
        
            #print 'win times:', v_sum
            #print 'lose times:', l_sum
        
            prob = float(v_sum) / (float(v_sum) + float(l_sum))
            if prob >= max_prob:
                max_prob = prob            
            
        #print 'win_prob', max_prob
        return max_prob
        
        
    def get_cards_score(self, hand, board):
        evaluator = Evaluator()
        p1_score = evaluator.evaluate(board, hand)
        
        return p1_score
    
