import json
import math
import os
import re
import requests

PLAYERS_NAMES = ['GKunchev', 'whiteknightuwu', 'georgi4c', 'StefSportsmann',
                'funvengeance', 'vbechev', 'Drdevil1234', 'vaseka', 'DK97',
                'Baskarov25', 'nikolaiberchev', 'psakutov']
TIME_PERIOD_REGEX = re.compile('.+/2021/0[34567]')

class BotezGambits:
    '''Collect Botez gambit moves between list of players.'''

    API_ROOT = 'https://api.chess.com/pub'
    EXPORT = 'games.json'

    def __init__(self, players, time_period):
        '''Constructor.'''
        self._players = players
        self._time_period = time_period
        self._games = []
        self._run()

    def _run(self):
        '''Run the procedure to collect games.'''
        self._init_games()
        self._collect_botez_gambits()

    def _get_data(self, endpoint, whole_link=False):
        '''Get data for an API endpoint.'''
        if whole_link:
            link = endpoint
        else:
            link = '{}/{}'.format(self.API_ROOT, endpoint)
        response = requests.get(link)
        if response.status_code == 200:
            return json.loads(response.content)

    def _filter_games(self, games):
        '''Filter games to only include known players.'''
        result = []
        for game in games:
            if game['white']['username'] in PLAYERS_NAMES:
                if game['black']['username'] in PLAYERS_NAMES:
                    result.append(game)
        return result

    def _register_games(self, games):
        '''Register games ensuring no duplicates.'''
        for new_game in games:
            for old_game in self._games:
                if old_game['url'] == new_game['url']:
                    break
            else:
                self._games.append(new_game)

    def _collect_games(self):
        '''Collect all games for all players.'''
        for player in self._players:
            archive_list_endpoint = 'player/{}/games/archives'.format(player)
            archive_list = self._get_data(archive_list_endpoint)
            for archive in archive_list['archives']:
                if self._time_period.match(archive):
                    games = self._get_data(archive, whole_link=True)
                    self._register_games(self._filter_games(games['games']))

    def _get_moves_list(self, pgn):
        '''Get moves list from pgn.'''
        # Get moves from pgn
        moves = pgn.split('\n\n')[1]
        # Remove clicks
        moves = re.sub(r'\{.+?\}', '', moves)
        # Unify white/black moves
        moves = moves.replace('...', '.')
        # Remove result
        moves = moves.replace('1-0', '')
        moves = moves.replace('0-1', '')
        moves = moves.replace('1/2-1/2', '')
        # Remove new lines and trailing spaces
        moves = moves.strip('\n').strip()
        # Remove extra spaces
        moves = re.sub(r'\s(\s)+?', ' ', moves)
        # Split to get only moves
        moves = re.split(r'\s?\d+\.\s?', moves)
        # Remove first element that is always empty due to the split
        moves = moves[1:]
        return moves

    def _get_botez_gambit(self, moves):
        '''Check moves for Botez gambit.'''
        # TODO: Probably this should be extended for cases in which
        #       a pawn is queened, but no need for this now.
        fallen_queen = None
        # Used to alternate colors
        flip_color = {
            'white': 'black',
            'black': 'white'
        }
        # Initial status
        status = {
            'white': 'd1',
            'black': 'd8',
            'to_move': 'white'
        }
        # Replay the game
        for i, move in enumerate(moves):
            # If the current move is not a take or a mare and a queen has
            # already fallen, this must a Botez gambit. As long as peices
            # are being exchanged since the queen fell, it's potentially
            # going to end up with a "clean" exchange.
            if fallen_queen is not None:
                if not 'x' in move and not '#' in move:
                    return fallen_queen
            # Check for queen taking
            opponent_queen = status[flip_color[status['to_move']]]
            if 'x{}'.format(opponent_queen) in move:
                if fallen_queen is not None:
                    # Nothing to see here, just a queen exchange
                    return None
                fallen_queen = math.ceil((i+1)/2), move
            # Check for queen move and update position if necessary
            if move.startswith('Q'):
                clean_move = move.replace('+', '')
                status[status['to_move']] = re.sub(r'Q(x)?', '', clean_move)
            # Alter colors
            status['to_move'] = flip_color[status['to_move']]


    def _init_games(self):
        '''Init game list.'''
        # Collect the games from external file if already exists
        if os.path.isfile(self.EXPORT):
            print("Using existing export file.")
            with open(self.EXPORT) as f:
                self._games = json.load(f)
        # ... or from the API if no run made yet
        else:
            print("Collecting data from API.")
            self._collect_games()
            with open(self.EXPORT, 'w') as f:
                json.dump(self._games, f)

    def _collect_botez_gambits(self):
        '''Looks for Botez gambits in the game list.'''
        for game in self._games:
            moves = self._get_moves_list(game['pgn'])
            botez_gambit = self._get_botez_gambit(moves)
            if botez_gambit is not None:
                print('=== {} vs {} ==='.format(game['white']['username'],
                                                game['black']['username']))
                print(game['url'])
                print(botez_gambit)


if __name__ == '__main__':
    BotezGambits(PLAYERS_NAMES, TIME_PERIOD_REGEX)
