from concurrent import futures
import logging
import uuid

import grpc

from login_pb2 import *
from login_pb2_grpc import *
from matchmaker_pb2 import *
from matchmaker_pb2_grpc import *
from character_sync_pb2 import *
from character_sync_pb2_grpc import *

update_time = 1.0

class Login(LoginServicer):
    users = []

    def GetUserToken(self, request, context):
        token = str(uuid.uuid4())
        Login.users.append({
            'name': request.name,
            'token': token,
        })
        return UserToken(token=token)

    def Logout(self, request, context):
        for user in Login.users:
            if user['token']==request.token:
                Login.users.remove(user)
                break
        return LogoutResult()

def validate_user_token(token):
    for user in Login.users:
        if user['token']==token:
            return True
    return False

class MatchMaker(MatchMakerServicer):
    games = []

    def CreateGame(self, request, context):
        if (validate_user_token(request.token)):
            game_id = str(uuid.uuid4())
            description = GameDescription(game_id=game_id, game_name=request.game_name)
            MatchMaker.games.append({
                'id': game_id,
                'name': request.game_name,
                'owner': request.token,
                'users': [],
                'characters': []
            })
            return GameCreationResult(creation_successful=True, game_description=description)
        else:
            return GameCreationResult(creation_successful=False)
    
    def GetActiveGames(self, request, context):
        games = []
        for game in MatchMaker.games:
            games.append(GameDescription(game_name=game['name'], game_id=game['id']))
        return GameList(games=games)
    
    def ConnectToGame(self, request, context):
        for game in MatchMaker.games:
            if game['id']==request.game_id:
                remove_user_from_all_games(request.user_token)
                game['users'].append(request.user_token)
                return GameConnectionResult(connection_successful=True)
        return GameConnectionResult(connection_successful=False)
    
    def DisconnectFromGame(self, request, context):
        remove_user_from_all_games(request.user_token)
        return GameDisconnectionRequest()

def remove_user_from_all_games(token):
    for game in MatchMaker.games:
        if token in game['users']:
            game['users'].remove(token)
    return

def find_game(id):
    for game in MatchMaker.games:
        if game['id']==id:
            return game
    return None

class CharacterSync(CharacterSyncServicer):

    last_updated_time = 0

    def UpdateCharacterWorldStates(self, request, context):
        game = find_game(request.game_id)
        if not game:
            return UpdateCharacterWorldStateResult()
        if request.update_time > CharacterSync.last_updated_time:
            update_characters(game, request.character_data, CharacterSync.last_updated_time, request.update_time)
            CharacterSync.last_updated_time = request.update_time
        return UpdateCharacterWorldStateResult()

    def GetCharacterWorldStates(self, request, context):
        game = find_game(request.game_id)
        if not game:
            return CharacterWorldStates()
        print(game['characters'])
        return CharacterWorldStates(game_id=request.game_id, character_data=game['characters'], update_time=CharacterSync.last_updated_time)
    
    def GetPlayerWorldStates(self, request, context):
        game = find_game(request.game_id)
        if not game:
            return CharacterWorldStates()
        output = []
        for character in game['characters']:
            if character.is_player:
                output.append(character)
        return CharacterWorldStates(game_id=request.game_id, character_data=output, update_time=CharacterSync.last_updated_time)

    def UpdatePersonalWorldState(self, request, context):
        game = find_game(request.game_id)
        if not game:
            return UpdatePersonalWorldStateResult()
        # print(request)
        for character in game['characters']:
            if character.id==request.world_state.id:
                # character.trajectory.x = (request.world_state.location.x - character.location.x) / 10.0
                # character.trajectory.y = 0
                # character.trajectory.z = (request.world_state.location.z - character.location.z) / 10.0
                # print(old_item.trajectory)
                character.location.x = request.world_state.location.x
                character.location.y = request.world_state.location.y
                character.location.z = request.world_state.location.z
                character.orientation.x = request.world_state.orientation.x
                character.orientation.y = request.world_state.orientation.y
                character.orientation.z = request.world_state.orientation.z
                character.orientation.w = request.world_state.orientation.w
                if request.world_state.HasField('animation_state'):
                    character.animation_state.state = request.world_state.animation_state.state
                if request.world_state.HasField('model_data') and request.world_state.model_data.HasField('player_appearance'):
                    character.model_data.player_appearance.fur_type = request.world_state.model_data.player_appearance.fur_type
                elif request.world_state.HasField('model_data') and request.world_state.model_data.HasField('monster_prefab'):
                    character.model_data.monster_prefab.prefab_name = request.world_state.model_data.monster_prefab.prefab_name
                character.health_and_status.level = request.world_state.health_and_status.level
                character.health_and_status.hp = request.world_state.health_and_status.hp
                character.health_and_status.max_hp = request.world_state.health_and_status.max_hp
                return UpdateCharacterWorldStateResult()
        game['characters'].append(request.world_state)
        return UpdateCharacterWorldStateResult()

    def GetPersonalWorldState(self, request, context):
        game = find_game(request.game_id)
        if not game:
            return CharacterWorldState()
        for character in game['characters']:
            if character.id==request.character_id:
                return character
        return CharacterWorldState()

def update_characters(game, data, old_time, new_time):
    for item in data:
        update_character(game, item, old_time, new_time)

def update_character(game, item, old_time, new_time):
    for old_item in game['characters']:
        if old_item.id==item.id:
            old_item.trajectory.x = (item.location.x - old_item.location.x) / 4.0 
            old_item.trajectory.y = 0 # (item.location.y - old_item.location.y) / (new_time - old_time)
            old_item.trajectory.z = (item.location.z - old_item.location.z) / 4.0
            # print(old_item.trajectory)
            old_item.location.x = item.location.x
            old_item.location.y = item.location.y
            old_item.location.z = item.location.z
            old_item.animation_state.state = item.animation_state.state
            old_item.health_and_status.level = item.health_and_status.level
            old_item.health_and_status.hp = item.health_and_status.hp
            old_item.health_and_status.max_hp = item.health_and_status.max_hp
            return
    game['characters'].append(item)

def main():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_LoginServicer_to_server(Login(), server)
    add_MatchMakerServicer_to_server(MatchMaker(), server)
    add_CharacterSyncServicer_to_server(CharacterSync(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    logging.basicConfig()
    main()
