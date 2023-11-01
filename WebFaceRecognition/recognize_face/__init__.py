class StatisticsArray:
    def __init__(self):
        self.array = [[], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []]
        self.index = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]


Statistics = StatisticsArray()


class NameDetect:
    def __init__(self):
        self.final_name = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]


Name = NameDetect()


class ClassNumberOfPeople:
    def __init__(self):
        self.get_num = 100


NumberOfPeople = ClassNumberOfPeople()


class Probabilities:
    def __init__(self):
        self.result = 0


probabilities = Probabilities()
