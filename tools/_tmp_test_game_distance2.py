from utils.game_utils import get_game_distance
pairs = [
    ((764,883),(782,476)),
    ((869,519),(870,210)),
    ((187,694),(654,654)),
    ((1335,694),(1799,654)),
]
for a,b in pairs:
    print("player:", a, "enemy:", b, "->", get_game_distance(a,b))
