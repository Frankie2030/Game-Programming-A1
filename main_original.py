##############################################
#   Assignment 1 - Game Programming - Semester 222
#
#   Group:
#   Phạm Duy Quang - 2011899
#   Nguyễn Vương Long - 1911520
#   Trương Tuấn Cường - 2012775
#   Nguyễn Duy Hà - 2011130
##############################################

import pygame
import random
import math
import time
from pygame import *
from Classes.GameDefine import Constants
from Classes.GameDefine import Zombie
from Classes.SoundEffect import SoundEffect

class Game:
    def __init__(self):
        # Initialize screen and title
        self.screen = pygame.display.set_mode((Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT))
        pygame.display.set_caption(Constants.GAME_TITLE)
        self.icon = pygame.image.load(Constants.ICON)
        pygame.display.set_icon(self.icon)
        self.background = pygame.image.load(Constants.IMAGE_BG)
        self.gameover = pygame.image.load(Constants.IMAGE_GAMEOVER)
        self.button1 = pygame.image.load(Constants.IMAGE_BUTTON_1)
        self.button2 = pygame.image.load(Constants.IMAGE_BUTTON_2)

        # Font for displaying text
        self.font_obj = pygame.font.Font(Constants.FONT_NAME, Constants.FONT_SIZE)

        # Initialize game statistics
        self.hits = 0
        self.misses = 0
        self.level = 1
        self.brains = 3
        self.zombie_count = 0

        # Initialize a queue of existing zombies
        self.zombie = []

        # Position of the graves in background
        self.grave_positions = []
        self.grave_positions.append(Constants.GRAVE_POS_1)
        self.grave_positions.append(Constants.GRAVE_POS_2)
        self.grave_positions.append(Constants.GRAVE_POS_3)
        self.grave_positions.append(Constants.GRAVE_POS_4)
        self.grave_positions.append(Constants.GRAVE_POS_5)
        self.grave_positions.append(Constants.GRAVE_POS_6)
        self.grave_positions.append(Constants.GRAVE_POS_7)
        self.grave_positions.append(Constants.GRAVE_POS_8)
        self.grave_positions.append(Constants.GRAVE_POS_9)
        self.grave_positions.append(Constants.GRAVE_POS_10)

        # Initialize zombie's sprite sheet - 6 states
        zombie_sprite_sheet = pygame.image.load(Constants.IMAGE_ZOMBIE)
        self.zombie_image = []
        self.zombie_image.append(zombie_sprite_sheet.subsurface(Constants.ZOM_SPRITE_1))
        self.zombie_image.append(zombie_sprite_sheet.subsurface(Constants.ZOM_SPRITE_2))
        self.zombie_image.append(zombie_sprite_sheet.subsurface(Constants.ZOM_SPRITE_3))
        self.zombie_image.append(zombie_sprite_sheet.subsurface(Constants.ZOM_SPRITE_4))
        self.zombie_image.append(zombie_sprite_sheet.subsurface(Constants.ZOM_SPRITE_5))
        self.zombie_image.append(zombie_sprite_sheet.subsurface(Constants.ZOM_SPRITE_6))

        # Initialize hammer image
        self.hammer_image = pygame.image.load(Constants.IMAGE_HAMMER).convert_alpha()
        self.hammer_image_rotate = transform.rotate(self.hammer_image.copy(), Constants.HAMMER_ANGLE)

        # Initialize sound effects
        self.soundEffect = SoundEffect()

        # Initialize brains
        self.brain_image = pygame.transform.scale(pygame.image.load(Constants.IMAGE_BRAIN), (40, 35))

    # Calculate the level up based on current hit & LEVEL_HIT_GAP
    def getPlayerLevel(self):
        nextLevel = int(self.hits / Constants.LEVEL_UP_GAP) + 1
        if nextLevel != self.level:
            self.soundEffect.playLevelUpSound() # Play sound level up
            self.brains += 1
        return nextLevel

    # Calculate the time zombie would stay
    def getStayTime(self):
        maxStayTime = Constants.STAY_TIME - self.level * Constants.STAY_DELTA_TIME
        if maxStayTime <= Constants.RESPAWN_DELTA_TIME:
            maxStayTime = Constants.RESPAWN_DELTA_TIME
        return maxStayTime

    # Calculate the time respawning new zombie
    def getRespawnTime(self):
        maxRespawnTime = Constants.RESPAWN_TIME - self.level * Constants.RESPAWN_DELTA_TIME
        if maxRespawnTime <= Constants.RESPAWN_DELTA_TIME:
            maxRespwanTime = Constants.RESPAWN_DELTA_TIME
        return maxRespawnTime

    # Check if the mouse hits zombie or not
    def isZombieHit(self, mouse_position):
        mouse_x = mouse_position[0]
        mouse_y = mouse_position[1]
        for zombieIndex in range(self.zombie_count):
            thisZombie = self.zombie[zombieIndex]
            if thisZombie.zombieStatus == 2:
                continue
            distanceX = mouse_x - self.grave_positions[thisZombie.index][0]
            distanceY = mouse_y - self.grave_positions[thisZombie.index][1]
            if (0 < distanceX < Constants.ZOM_WIDTH) and (0 < distanceY < Constants.ZOM_HEIGHT):
                return zombieIndex
        return -1

    # Generate a new zombie
    def generateZombie(self):
        if self.zombie_count >= Constants.ZOM_NUM_MAX:
            return 0
        spawnIndex = random.randint(0, Constants.GRAVE_NUM_MAX - 1)
        for zombieIndex in range(self.zombie_count):
            if self.zombie[zombieIndex].index == spawnIndex:
                return 0
        newZombie = Zombie(spawnIndex, self.zombie_image[0])
        self.zombie.append(newZombie)
        self.zombie_count += 1
        return 1

    # Calculate player's brains
    def update_brain(self, isEaten):
        if isEaten:
            self.brains -= 1

        self.screen.blit(self.brain_image, (650, 18))

    # Update, rotate the hammer
    def update_hammer(self, mouse_position, image, image_rotate, isClicked):
        mouse_x = mouse_position[0] - Constants.HAMMER_DISTANCE_X
        mouse_y = mouse_position[1] - Constants.HAMMER_DISTANCE_Y
        if isClicked:
            self.screen.blit(image_rotate, [mouse_x, mouse_y])
        else:
            self.screen.blit(image, [mouse_x, mouse_y])

    # Update zombie's animation
    def update_sprite(self):
        self.screen.blit(self.background, (0, 0))
        for zombieIndex in range(self.zombie_count):
            thisZombie = self.zombie[zombieIndex]
            self.screen.blit(thisZombie.pic, (self.grave_positions[thisZombie.index]))

    # Update player's hits, misses, level, brains
    def update_statistics(self, isClicked, isEaten):
        self.update_hammer(mouse.get_pos(), self.hammer_image, self.hammer_image_rotate, isClicked)
        self.update_brain(isEaten)

        # Update the player's hits
        current_hit_string = Constants.HIT_TEXT + str(self.hits)
        hit_text = self.font_obj.render(current_hit_string, True, Constants.TEXT_COLOR)
        hit_text_pos = hit_text.get_rect()
        hit_text_pos.centerx = Constants.HIT_POS
        hit_text_pos.centery = Constants.FONT_SIZE
        self.screen.blit(hit_text, hit_text_pos)

        # Update the player's misses
        current_misses_string = Constants.MISS_TEXT + str(self.misses)
        misses_text = self.font_obj.render(current_misses_string, True, Constants.TEXT_COLOR)
        misses_text_pos = misses_text.get_rect()
        misses_text_pos.centerx = Constants.MISS_POS
        misses_text_pos.centery = Constants.FONT_SIZE
        self.screen.blit(misses_text, misses_text_pos)

        # Update the player's level
        current_level_string = Constants.LEVEL_TEXT + str(self.level)
        level_text = self.font_obj.render(current_level_string, True, Constants.TEXT_COLOR)
        level_text_pos = level_text.get_rect()
        level_text_pos.centerx = Constants.LEVEL_POS
        level_text_pos.centery = Constants.FONT_SIZE
        self.screen.blit(level_text, level_text_pos)

        # Update the player's brain count
        current_level_string = Constants.BRAIN_COUNT + str(self.brains)
        level_text = self.font_obj.render(current_level_string, True, Constants.TEXT_COLOR)
        level_text_pos = level_text.get_rect()
        level_text_pos.centerx = Constants.BRAIN_POS
        level_text_pos.centery = Constants.FONT_SIZE
        self.screen.blit(level_text, level_text_pos)

    # Show game over screen
    def showEndScreen(self):
        fontEnd = pygame.font.Font(Constants.FONT_NAME, 64)
        missImage = fontEnd.render(str(self.misses), True, (255, 255, 255))
        hitImage = fontEnd.render(str(self.hits), True, (255,255, 255))
        score = self.hits - self.misses
        if score < 0:
            score = 0
        scoreImage = fontEnd.render(str(score), True, (255,255, 255))
        self.screen.blit(self.gameover, (0, 0))
        self.screen.blit(self.button1, (278, 509))
        self.screen.blit(missImage, (580, 364))
        self.screen.blit(hitImage, (311, 364))
        self.screen.blit(scoreImage, (507, 444))
        mouseX, mouseY = pygame.mouse.get_pos()
        if mouseX >= 278 and mouseX <= 557 and mouseY >= 509 and mouseY <= 559:
            self.screen.blit(self.button2, (278, 509))
    # Start the game's main loop
    def start(self):
        # Start screen
        startScreen = pygame.image.load(Constants.IMAGE_START)
        button0 = pygame.image.load(Constants.IMAGE_BUTTON_0)
        button0_hover = pygame.image.load(Constants.IMAGE_BUTTON_0_HOVER)
        gameStart = False
        while not gameStart:
            self.screen.blit(startScreen, (0, 0))
            self.screen.blit(button0, (527, 352))
            mouseX, mouseY = pygame.mouse.get_pos()
            if mouseX >= 527 and mouseX <= 794 and mouseY >= 352 and mouseY <= 406:
                self.screen.blit(button0_hover, (527, 352))
            pygame.display.update()
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if mouseX >= 527 and mouseX <= 794 and mouseY >= 352 and mouseY <= 406:
                        gameStart = True
                if event.type == pygame.QUIT:
                    pygame.quit()

        # Game settings
        loop = True
        mouse.set_visible(False)

        # Flag variables
        isClicked = False
        isEaten = False

        # Time variables
        clock = pygame.time.Clock()     # Time variables
        cycle_time = 0                  # Count clock's time
        gameTime = 0
        lastSpawnTime = 0

        # Zombie-spawning variables
        maxStayTime = 5
        respawnTime = 1.5
        hitPos = -1

        for i in range(len(self.zombie_image)):
            self.zombie_image[i].set_colorkey((0, 0, 0))
            self.zombie_image[i] = self.zombie_image[i].convert_alpha()

        while loop:
            if self.brains > 0:
                # Calculate game input
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        loop = False
                    if event.type == MOUSEBUTTONDOWN and event.button == Constants.LEFT_MOUSE_BUTTON:
                        isClicked = True
                        hitPos = self.isZombieHit(mouse.get_pos())
                        if hitPos != -1:
                            self.zombie[hitPos].zombieStatus = 2
                            self.hits += 1
                            self.level = self.getPlayerLevel()
                            maxStayTime = self.getStayTime()
                            respawnTime = self.getRespawnTime()
                            self.soundEffect.playHitSound() # Play hit sound effect
                        else:
                            self.misses += 1
                            self.soundEffect.playMissSound() # Play miss sound effect
                    else:
                        isClicked = False

                # Calculate game time
                mil = clock.tick(Constants.FPS)
                sec = mil / 1000.0
                cycle_time += sec
                gameTime += sec

                # Calculate zombies' variables
                zombieIndex = 0
                while zombieIndex < self.zombie_count:
                    thisZombie = self.zombie[zombieIndex]
                    thisZombie.stayTime += sec

                    # Zombie status: rise
                    if thisZombie.zombieStatus == 0:
                        if  thisZombie.stayTime > Constants.SPAWN_ANI_TIME:
                            if thisZombie.animationIndex > Constants.SPAWN_ANI_INDEX_MAX:
                                if thisZombie.stayTime > maxStayTime:
                                    thisZombie.animationIndex = Constants.SPAWN_ANI_INDEX_MAX
                                    thisZombie.zombieStatus = 1
                                    thisZombie.stayTime = 0
                                    continue
                            else:
                                thisZombie.pic = self.zombie_image[thisZombie.animationIndex]
                                thisZombie.animationIndex += 1
                                thisZombie.stayTime = 0

                    # Zombie status: run away
                    if thisZombie.zombieStatus == 1:
                        if thisZombie.stayTime > Constants.SPAWN_ANI_TIME:
                            if thisZombie.animationIndex >= 0:
                                thisZombie.pic = self.zombie_image[thisZombie.animationIndex]
                            thisZombie.animationIndex -= 1
                            thisZombie.stayTime = 0
                            # Make sure the last frame doesn't last one frame
                            if thisZombie.animationIndex < -1:
                                self.zombie.pop(zombieIndex)
                                self.zombie_count -= 1
                                isEaten = True
                                continue

                    # Zombie status: dead
                    if thisZombie.zombieStatus == 2:
                        if thisZombie.stayTime > Constants.DEAD_ANI_TIME:
                            if thisZombie.animationIndex < Constants.DEAD_ANI_INDEX_MAX:
                                thisZombie.pic = self.zombie_image[thisZombie.animationIndex]
                            thisZombie.animationIndex += 1
                            thisZombie.stayTime = 0
                            if thisZombie.animationIndex > Constants.DEAD_ANI_INDEX_MAX:
                                self.zombie.pop(zombieIndex)
                                self.zombie_count -= 1
                                continue

                    zombieIndex += 1

                self.update_sprite()
                self.update_statistics(isClicked, isEaten)
                if gameTime - lastSpawnTime > respawnTime:
                    if self.generateZombie():
                        lastSpawnTime = gameTime

                isEaten = False

                # Update the display
                pygame.display.flip()

            else:
                mouse.set_visible(True)
                self.showEndScreen()
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        loop = False
                    if event.type == MOUSEBUTTONDOWN and event.button == Constants.LEFT_MOUSE_BUTTON:
                        mouseX, mouseY = pygame.mouse.get_pos()
                        if mouseX >= 278 and mouseX <= 557 and mouseY >= 509 and mouseY <= 559:
                            self.brains = 3
                            self.hits = 0
                            self.misses = 0
                            self.level = 1
                            self.zombie_count = 0

                            # Initialize a queue of existing zombies
                            self.zombie = []
                            clock = pygame.time.Clock()     # Time variables
                            cycle_time = 0                  # Count clock's time
                            gameTime = 0
                            lastSpawnTime = 0

                            # Zombie-spawning variables
                            maxStayTime = 5
                            respawnTime = 1.5
                            hitPos = -1

            pygame.display.update()
###########################################################################
# Initialize the game
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
pygame.init()

# Start game - Run main loop
myGame = Game()
myGame.start()

# Exit game if the main loop ends
pygame.quit()