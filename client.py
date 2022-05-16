from pprint import pprint as print
import socket
import select
import pygame
from macros import *
from entities import *
import pickle
import traceback


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.connect((SERVER_IP, SERVER_PORT))

pygame.init()

font = pygame.font.SysFont('arial',  10)
screen = pygame.display.set_mode((WIDTH, HEIGHT), flags=pygame.SCALED)
pygame.display.set_caption("Fight Club")
clock = pygame.time.Clock()

id = None
all_sprites = None
main_player = None

running = True
while running:
    ready_sockets, _, _ = select.select([server], [], [], CLIENT_TIMEOUT)

    try:
        if ready_sockets:
            try:
                data = pickle.loads(server.recv(1024))
            except Exception:
                continue

            if isinstance(data, str) and data == 'kill':
                print(data)
                exit('Killed by server')

            if id is None and not isinstance(data, str):
                continue

            elif id is None and isinstance(data, str):
                id = data
                continue

            elif id is not None and not isinstance(data, dict):
                continue

            elif id is not None and isinstance(data, dict):
                enemies = pygame.sprite.Group()
                players = pygame.sprite.Group()
                ui = pygame.sprite.Group()
                all_sprites = pygame.sprite.Group()

                for player_entity in data['players']:
                    if player_entity['id'] == id:
                        color = PURPLE
                    else:
                        color = BLUE

                    sprite = PlayerSprite(entity=player_entity, color=color)

                    ui.add(HealthBarSprite(sprite))
                    ui.add(EntityNameSprite(sprite, font, 'Player'))

                    if (player_entity['id'] == id and
                            player_entity['stats']['speaking'] == 'writing'):
                        ui.add(ChatBubbleSprite(sprite, font, color=DARKGREY))

                    if player_entity['stats']['speaking'] == 'ready':
                        ui.add(
                            ChatBubbleSprite(sprite, font, color=LIGHTBLACK)
                        )

                    players.add(sprite)

                    if player_entity['id'] == id:
                        main_player = sprite
                        main_player.main = True

                for enemy_entity in data['enemies']:
                    sprite = EnemySprite(entity=enemy_entity, color=YELLOW)
                    ui.add(HealthBarSprite(sprite))
                    ui.add(EntityNameSprite(sprite, font, 'Enemy'))
                    enemies.add(sprite)

                all_sprites.add(players)
                all_sprites.add(enemies)
                all_sprites.add(ui)
            else:
                print(data)
                exit('strange result:')

            if all_sprites is None:
                continue
            else:
                clock.tick(FPS)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False

                all_sprites.update()

                hits = pygame.sprite.groupcollide(
                    players, all_sprites, False, False)

                response = {'commands': [], 'id': id}
                if hits:
                    for hitting in hits:
                        if hitting.stats['attacking']:
                            for hitted in hits[hitting]:
                                if hitted is not hitting:
                                    if isinstance(hitted, EnemySprite):
                                        command = 'damage: player-to-enemy'
                                    elif isinstance(hitted, PlayerSprite):
                                        command = 'damage: player-to-player'
                                    else:
                                        continue

                                    damage = CALCULATE_DAMAGE(
                                        hitting.stats, hitted.stats,
                                        NORMAL_ATTACK)
                                    new_hp = hitted.stats['hp']
                                    hitted.receive_damage(damage)

                                    damage_command = {
                                        'type': command,
                                        'hitting': hitting.entity,
                                        'hitted': hitted.entity
                                    }
                                    response['commands'].append(
                                        {'damage': damage_command}
                                    )

                if main_player is not None:
                    if main_player.stats['moving']:
                        response['commands'].append(
                            {'movement': main_player.entity})

                    if main_player.stats['animating']:
                        response['commands'].append(
                            {'animation': main_player.entity})

                    if main_player.stats['speaking']:
                        response['commands'].append(
                            {'speak': main_player.entity})

                if len(response['commands']):
                    response = {'action': 'commands', 'value': response}
                    server.send(pickle.dumps(response))

                screen.fill(BLACK)
                all_sprites.draw(screen)
                pygame.display.flip()

    except Exception as e:
        print('global error: ' + str(e))
        server.send(pickle.dumps({'action': 'error', 'value': {'error': e}}))
        traceback.print_exc()
        exit()

pygame.quit()
