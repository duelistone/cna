# ot_information.py

import time

class OT_Information(object):
    '''An object to store information of an opening test.'''
    def __init__(self):
        self.ot_progress = (0, 0) # Correct and total answered in session
        self.reset_question_info()

    def reset_time(self):
        self.starting_time = time.time()

    def reset_question_info(self):
        self.incorrect_answers = 0
        self.reset_time()

    def incorrect_answer(self):
        self.incorrect_answers += 1

    def update_progress(self, b):
        self.ot_progress = (self.ot_progress[0] + b, self.ot_progress[1] + 1) # Typecasting bool b to int

