##############################################
# Enhanced Whack-A-Zombie Game
# 
# Improvements:
# - Removed artificial rapid-click prevention
# - Relies on pygame's event system for clean click handling
# - Hit flash timer removed from hit detection
# - Fixed hit vs kill counting logic
# - Added separate kills stat
##############################################

import pygame
import random
import math
import time
from pygame import *
from Classes.GameDefine import Constants
from Classes.GameDefine import Zombie
from Classes.SoundEffect import SoundEffect

class ScreenEffect:
    def __init__(self):
        self.shake_timer = 0
        self.shake_intensity = 0
        self.blood_overlay_timer = 0
        self.damage_indicators = []
        
    def add_screen_shake(self, duration, intensity):
        self.shake_timer = duration
        self.shake_intensity = intensity
        
    def add_blood_overlay(self, duration):
        self.blood_overlay_timer = duration
        
    def add_damage_indicator(self, text, pos):
        self.damage_indicators.append({
            'text': text,
            'pos': pos,
            'timer': 2.0,
            'y_offset': 0
        })
        
    def update(self, dt):
        self.shake_timer = max(0, self.shake_timer - dt)
        self.blood_overlay_timer = max(0, self.blood_overlay_timer - dt)
        
        # Update damage indicators
        for indicator in self.damage_indicators[:]:
            indicator['timer'] -= dt
            indicator['y_offset'] -= 50 * dt  # Float upward
            if indicator['timer'] <= 0:
                self.damage_indicators.remove(indicator)
                
    def get_screen_offset(self):
        if self.shake_timer > 0:
            shake_x = random.randint(-self.shake_intensity, self.shake_intensity)
            shake_y = random.randint(-self.shake_intensity, self.shake_intensity)
            return (shake_x, shake_y)
        return (0, 0)
        
    def draw_blood_overlay(self, screen):
        if self.blood_overlay_timer > 0:
            alpha = int(128 * (self.blood_overlay_timer / Constants.BLOOD_OVERLAY_DURATION))
            blood_surface = pygame.Surface((Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT))
            blood_surface.set_alpha(alpha)
            blood_surface.fill((180, 0, 0))  # Dark red
            screen.blit(blood_surface, (0, 0))
            
    def draw_damage_indicators(self, screen, font):
        for indicator in self.damage_indicators:
            alpha = int(255 * (indicator['timer'] / 2.0))
            text_surface = font.render(indicator['text'], True, (255, 255, 255))
            text_surface.set_alpha(alpha)
            pos = (indicator['pos'][0], indicator['pos'][1] + indicator['y_offset'])
            screen.blit(text_surface, pos)

class Particle:
    def __init__(self, x, y, vx, vy, color, life):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 200 * dt  # Gravity
        self.life -= dt
        return self.life > 0
        
    def draw(self, screen):
        alpha = int(255 * (self.life / self.max_life))
        color = (*self.color, alpha)
        try:
            pygame.gfxdraw.filled_circle(screen, int(self.x), int(self.y), 3, color)
        except:
            pygame.draw.circle(screen, self.color[:3], (int(self.x), int(self.y)), 3)

class ParticleSystem:
    def __init__(self):
        self.particles = []
        
    def add_hit_particles(self, x, y):
        for _ in range(8):
            vx = random.uniform(-100, 100)
            vy = random.uniform(-150, -50)
            color = (255, 255, 0)  # Yellow
            life = random.uniform(0.5, 1.0)
            self.particles.append(Particle(x, y, vx, vy, color, life))
            
    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]
        
    def draw(self, screen):
        for particle in self.particles:
            particle.draw(screen)

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
        self.small_font = pygame.font.Font(Constants.FONT_NAME, 24)

        # Initialize game statistics
        self.hits = 0        # Successful hits on zombies (including non-lethal hits)
        self.kills = 0       # Zombies actually killed
        self.misses = 0
        self.level = 1
        self.brains = 3
        self.zombie_count = 0
        self.total_shots = 0

        # HUD toggle states
        self.show_fps = False
        self.show_accuracy = False
        self.fps_samples = []
        
        # Click handling - rely on pygame event system to prevent double-counting
        
        # Pause state
        self.paused = False

        # Initialize enhanced systems
        self.screen_effects = ScreenEffect()
        self.particle_system = ParticleSystem()

        # Initialize a queue of existing zombies
        self.zombie = []

        # Position of the graves in background
        self.grave_positions = [
            Constants.GRAVE_POS_1, Constants.GRAVE_POS_2, Constants.GRAVE_POS_3,
            Constants.GRAVE_POS_4, Constants.GRAVE_POS_5, Constants.GRAVE_POS_6,
            Constants.GRAVE_POS_7, Constants.GRAVE_POS_8, Constants.GRAVE_POS_9,
            Constants.GRAVE_POS_10
        ]

        # Initialize zombie sprite sheets
        zombie_sprite_sheet = pygame.image.load(Constants.IMAGE_ZOMBIE)
        self.zombie_image = []
        self.zombie_image.append(zombie_sprite_sheet.subsurface(Constants.ZOM_SPRITE_1))
        self.zombie_image.append(zombie_sprite_sheet.subsurface(Constants.ZOM_SPRITE_2))
        self.zombie_image.append(zombie_sprite_sheet.subsurface(Constants.ZOM_SPRITE_3))
        self.zombie_image.append(zombie_sprite_sheet.subsurface(Constants.ZOM_SPRITE_4))
        self.zombie_image.append(zombie_sprite_sheet.subsurface(Constants.ZOM_SPRITE_5))
        self.zombie_image.append(zombie_sprite_sheet.subsurface(Constants.ZOM_SPRITE_6))

        # Initialize attack animation sprites
        self.zombie_attack_frames = []
        self.zombie_attack_frames.append(zombie_sprite_sheet.subsurface(Constants.ZOM_ATTACK_1))
        self.zombie_attack_frames.append(zombie_sprite_sheet.subsurface(Constants.ZOM_ATTACK_2))
        self.zombie_attack_frames.append(zombie_sprite_sheet.subsurface(Constants.ZOM_ATTACK_3))
        self.zombie_attack_frames.append(zombie_sprite_sheet.subsurface(Constants.ZOM_ATTACK_4))

        # Initialize hammer image
        self.hammer_image = pygame.image.load(Constants.IMAGE_HAMMER).convert_alpha()
        self.hammer_image_rotate = transform.rotate(self.hammer_image.copy(), Constants.HAMMER_ANGLE)

        # Initialize sound effects
        self.soundEffect = SoundEffect()

        # Initialize brains
        self.brain_image = pygame.transform.scale(pygame.image.load(Constants.IMAGE_BRAIN), (40, 35))

        # Initialize all sprite transparency
        for i in range(len(self.zombie_image)):
            self.zombie_image[i].set_colorkey((0, 0, 0))
            self.zombie_image[i] = self.zombie_image[i].convert_alpha()
        
        for i in range(len(self.zombie_attack_frames)):
            self.zombie_attack_frames[i].set_colorkey((0, 0, 0))
            self.zombie_attack_frames[i] = self.zombie_attack_frames[i].convert_alpha()

    def getPlayerLevel(self):
        nextLevel = int(self.hits / Constants.LEVEL_UP_GAP) + 1
        if nextLevel != self.level:
            self.soundEffect.playLevelUpSound()
            self.brains += 1  # Keep brain reward on level up as requested
        return nextLevel

    def getStayTime(self):
        maxStayTime = Constants.STAY_TIME - self.level * Constants.STAY_DELTA_TIME
        if maxStayTime <= Constants.RESPAWN_DELTA_TIME:
            maxStayTime = Constants.RESPAWN_DELTA_TIME
        return maxStayTime

    def getRespawnTime(self):
        maxRespawnTime = Constants.RESPAWN_TIME - self.level * Constants.RESPAWN_DELTA_TIME
        if maxRespawnTime <= Constants.RESPAWN_DELTA_TIME:
            maxRespawnTime = Constants.RESPAWN_DELTA_TIME
        return maxRespawnTime

    def get_zombie_type_for_level(self):
        """Determine zombie type based on level for progressive difficulty"""
        if self.level <= 2:
            return Constants.ZOM_TYPE_NORMAL
        elif self.level <= 4:
            return random.choice([Constants.ZOM_TYPE_NORMAL, Constants.ZOM_TYPE_CONE])
        else:
            return random.choice([Constants.ZOM_TYPE_NORMAL, Constants.ZOM_TYPE_CONE, Constants.ZOM_TYPE_BUCKET])

    def isZombieHit(self, mouse_position):
        """Check if mouse hits a zombie. Only allow hits on fully emerged zombies."""
        mouse_x = mouse_position[0]
        mouse_y = mouse_position[1]
        for zombieIndex in range(self.zombie_count):
            thisZombie = self.zombie[zombieIndex]
            
            # Only allow hits on zombies that are fully emerged and not in special states
            if thisZombie.zombieStatus != 0:  # Not in rising state
                continue
            if thisZombie.animationIndex <= Constants.SPAWN_ANI_INDEX_MAX:  # Still emerging
                continue
                
            distanceX = mouse_x - self.grave_positions[thisZombie.index][0]
            distanceY = mouse_y - self.grave_positions[thisZombie.index][1]
            if (0 < distanceX < Constants.ZOM_WIDTH) and (0 < distanceY < Constants.ZOM_HEIGHT):
                return zombieIndex
        return -1

    def generateZombie(self):
        if self.zombie_count >= Constants.ZOM_NUM_MAX:
            return 0
        spawnIndex = random.randint(0, Constants.GRAVE_NUM_MAX - 1)
        for zombieIndex in range(self.zombie_count):
            if self.zombie[zombieIndex].index == spawnIndex:
                return 0
        
        zombie_type = self.get_zombie_type_for_level()
        newZombie = Zombie(spawnIndex, self.zombie_image[0], zombie_type)
        self.zombie.append(newZombie)
        self.zombie_count += 1
        return 1

    def hit_zombie(self, zombie_index):
        """Handle zombie being hit - supports multi-hit system"""
        zombie = self.zombie[zombie_index]
        zombie.current_health -= 1
        zombie.hit_flash_timer = Constants.HIT_FLASH_DURATION
        
        # Add hit particles at zombie position
        zombie_pos = self.grave_positions[zombie.index]
        self.particle_system.add_hit_particles(
            zombie_pos[0] + Constants.ZOM_WIDTH // 2,
            zombie_pos[1] + Constants.ZOM_HEIGHT // 2
        )
        
        # Add damage number
        self.screen_effects.add_damage_indicator(
            "1", 
            (zombie_pos[0] + Constants.ZOM_WIDTH // 2 - 10, zombie_pos[1])
        )
        
        if zombie.current_health <= 0:
            zombie.zombieStatus = 2  # Dead
            self.soundEffect.playHitSound()
            return True  # Zombie killed
        else:
            zombie.zombieStatus = 0  # Back to rising state, reset animation
            zombie.animationIndex = max(0, zombie.animationIndex - 1)
            self.soundEffect.playZombieHurtSound()
            return False  # Zombie hurt but not killed

    def draw_health_bar(self, zombie):
        """Draw health bar above multi-hit zombies"""
        # if zombie.max_health <= 1:
        #     return
            
        pos = self.grave_positions[zombie.index]
        bar_width = Constants.ZOM_WIDTH
        bar_height = 6
        bar_x = pos[0]
        bar_y = pos[1] - 15
        
        # Background bar (red)
        pygame.draw.rect(self.screen, (200, 0, 0), 
                        (bar_x, bar_y, bar_width, bar_height))
        
        # Health bar (color-coded)
        health_percent = zombie.current_health / zombie.max_health
        health_width = int(bar_width * health_percent)
        
        if health_percent > 0.66:
            color = (0, 200, 0)  # Green
        elif health_percent > 0.33:
            color = (200, 200, 0)  # Yellow  
        else:
            color = (200, 100, 0)  # Orange
            
        if health_width > 0:
            pygame.draw.rect(self.screen, color, 
                            (bar_x, bar_y, health_width, bar_height))
        
        # Border
        pygame.draw.rect(self.screen, (255, 255, 255), 
                        (bar_x, bar_y, bar_width, bar_height), 1)

    def update_brain(self, isEaten):
        if isEaten:
            self.brains -= 1
        self.screen.blit(self.brain_image, (650, 18))

    def update_hammer(self, mouse_position, image, image_rotate, isClicked):
        # Apply screen shake offset
        shake_offset = self.screen_effects.get_screen_offset()
        mouse_x = mouse_position[0] - Constants.HAMMER_DISTANCE_X + shake_offset[0]
        mouse_y = mouse_position[1] - Constants.HAMMER_DISTANCE_Y + shake_offset[1]
        
        if isClicked:
            self.screen.blit(image_rotate, [mouse_x, mouse_y])
        else:
            self.screen.blit(image, [mouse_x, mouse_y])

    def update_sprite(self):
        # Apply screen shake to background
        shake_offset = self.screen_effects.get_screen_offset()
        self.screen.blit(self.background, shake_offset)
        
        for zombieIndex in range(self.zombie_count):
            thisZombie = self.zombie[zombieIndex]
            
            # Apply hit flash effect
            zombie_surface = thisZombie.pic.copy()
            if thisZombie.hit_flash_timer > 0:
                # Create red tint for hit flash
                flash_surface = pygame.Surface(zombie_surface.get_size())
                flash_surface.fill((255, 100, 100))
                zombie_surface.blit(flash_surface, (0, 0), special_flags=pygame.BLEND_ADD)
                thisZombie.hit_flash_timer -= 1/60.0  # Assuming 60 FPS
            
            # Draw zombie with shake offset
            pos = self.grave_positions[thisZombie.index]
            final_pos = (pos[0] + shake_offset[0], pos[1] + shake_offset[1])
            self.screen.blit(zombie_surface, final_pos)
            
            # Draw health bar for multi-hit zombies
            self.draw_health_bar(thisZombie)

    def update_hud(self, fps):
        """Update HUD with toggleable elements"""
        current_kill_string = Constants.KILL_TEXT + str(self.kills)
        kill_text = self.font_obj.render(current_kill_string, True, Constants.TEXT_COLOR)
        kill_text_pos = kill_text.get_rect()
        kill_text_pos.centerx = Constants.KILL_POS
        kill_text_pos.centery = Constants.FONT_SIZE
        self.screen.blit(kill_text, kill_text_pos)

        current_hit_string = Constants.HIT_TEXT + str(self.hits)
        hit_text = self.font_obj.render(current_hit_string, True, Constants.TEXT_COLOR)
        hit_text_pos = hit_text.get_rect()
        hit_text_pos.centerx = Constants.HIT_POS
        hit_text_pos.centery = Constants.FONT_SIZE
        self.screen.blit(hit_text, hit_text_pos)

        current_misses_string = Constants.MISS_TEXT + str(self.misses)
        misses_text = self.font_obj.render(current_misses_string, True, Constants.TEXT_COLOR)
        misses_text_pos = misses_text.get_rect()
        misses_text_pos.centerx = Constants.MISS_POS
        misses_text_pos.centery = Constants.FONT_SIZE
        self.screen.blit(misses_text, misses_text_pos)

        current_level_string = Constants.LEVEL_TEXT + str(self.level)
        level_text = self.font_obj.render(current_level_string, True, Constants.TEXT_COLOR)
        level_text_pos = level_text.get_rect()
        level_text_pos.centerx = Constants.LEVEL_POS
        level_text_pos.centery = Constants.FONT_SIZE
        self.screen.blit(level_text, level_text_pos)

        current_brain_string = Constants.BRAIN_COUNT + str(self.brains)
        brain_text = self.font_obj.render(current_brain_string, True, Constants.TEXT_COLOR)
        brain_text_pos = brain_text.get_rect()
        brain_text_pos.centerx = Constants.BRAIN_POS
        brain_text_pos.centery = Constants.FONT_SIZE
        self.screen.blit(brain_text, brain_text_pos)

        # Toggleable HUD elements
        y_offset = 70
        
        if self.show_fps:
            # Update FPS samples for smoothing
            self.fps_samples.append(fps)
            if len(self.fps_samples) > 10:
                self.fps_samples.pop(0)
            avg_fps = sum(self.fps_samples) / len(self.fps_samples)
            
            # Color-code FPS
            if avg_fps >= 55:
                fps_color = (0, 255, 0)  # Green
            elif avg_fps >= 30:
                fps_color = (255, 255, 0)  # Yellow
            else:
                fps_color = (255, 0, 0)  # Red
                
            fps_text = self.small_font.render(f"FPS {avg_fps:.1f}", True, fps_color)
            self.screen.blit(fps_text, (10, y_offset))
            y_offset += 30

        if self.show_accuracy:
            if self.total_shots > 0:
                accuracy = (self.hits / self.total_shots) * 100
                
                # Color-code accuracy
                if accuracy >= 80:
                    acc_color = (0, 255, 0)  # Green
                elif accuracy >= 60:
                    acc_color = (255, 255, 0)  # Yellow
                elif accuracy >= 40:
                    acc_color = (255, 165, 0)  # Orange
                else:
                    acc_color = (255, 0, 0)  # Red
                    
                acc_text = self.small_font.render(f"ACC - {accuracy:.1f}%", True, acc_color)
                self.screen.blit(acc_text, (10, y_offset))
                y_offset += 30

        # Show mute status
        if self.soundEffect.muted:
            mute_text = self.small_font.render("MUTED", True, (255, 100, 100))
            self.screen.blit(mute_text, (Constants.SCREEN_WIDTH - 80, 10))

    def update_statistics(self, isClicked, isEaten):
        self.update_hammer(mouse.get_pos(), self.hammer_image, self.hammer_image_rotate, isClicked)
        self.update_brain(isEaten)

    def process_zombie_attack(self, zombie):
        """Handle zombie attack with enhanced feedback"""
        # Play attack sounds
        self.soundEffect.playZombieAttackSound()
        self.soundEffect.playPlayerHurtSound()
        
        # Add screen shake
        self.screen_effects.add_screen_shake(
            Constants.SCREEN_SHAKE_DURATION, 
            5  # Intensity
        )
        
        # Add blood overlay
        self.screen_effects.add_blood_overlay(Constants.BLOOD_OVERLAY_DURATION)
        
        # Add -1 brain damage indicator at brain display
        self.screen_effects.add_damage_indicator(
            "-1", 
            (Constants.BRAIN_POS, Constants.FONT_SIZE - 10)
        )

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

    def draw_volume_sliders(self, mouseX, mouseY):
        """Draw volume control sliders on the main menu"""
        # Volume control area
        settings_x = 50
        settings_y = 200
        slider_width = 200
        slider_height = 20
        
        # BGM Volume
        bgm_text = self.small_font.render("BGM Volume", True, (255, 255, 255))
        self.screen.blit(bgm_text, (settings_x, settings_y))
        
        # BGM slider background
        bgm_slider_rect = pygame.Rect(settings_x, settings_y + 30, slider_width, slider_height)
        pygame.draw.rect(self.screen, (100, 100, 100), bgm_slider_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), bgm_slider_rect, 2)
        
        # BGM slider handle
        bgm_handle_x = settings_x + int(self.soundEffect.get_bgm_volume() * slider_width) - 10
        bgm_handle_rect = pygame.Rect(bgm_handle_x, settings_y + 25, 20, 30)
        pygame.draw.rect(self.screen, (255, 100, 100), bgm_handle_rect)
        
        # BGM volume percentage
        bgm_percent = int(self.soundEffect.get_bgm_volume() * 100)
        bgm_percent_text = self.small_font.render(f"{bgm_percent}%", True, (255, 255, 255))
        self.screen.blit(bgm_percent_text, (settings_x + slider_width + 10, settings_y + 25))
        
        # SFX Volume
        sfx_y = settings_y + 80
        sfx_text = self.small_font.render("SFX Volume", True, (255, 255, 255))
        self.screen.blit(sfx_text, (settings_x, sfx_y))
        
        # SFX slider background
        sfx_slider_rect = pygame.Rect(settings_x, sfx_y + 30, slider_width, slider_height)
        pygame.draw.rect(self.screen, (100, 100, 100), sfx_slider_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), sfx_slider_rect, 2)
        
        # SFX slider handle
        sfx_handle_x = settings_x + int(self.soundEffect.get_sfx_volume() * slider_width) - 10
        sfx_handle_rect = pygame.Rect(sfx_handle_x, sfx_y + 25, 20, 30)
        pygame.draw.rect(self.screen, (100, 255, 100), sfx_handle_rect)
        
        # SFX volume percentage
        sfx_percent = int(self.soundEffect.get_sfx_volume() * 100)
        sfx_percent_text = self.small_font.render(f"{sfx_percent}%", True, (255, 255, 255))
        self.screen.blit(sfx_percent_text, (settings_x + slider_width + 10, sfx_y + 25))
        
        return bgm_slider_rect, sfx_slider_rect
    
    def handle_volume_slider_click(self, mouseX, mouseY, bgm_rect, sfx_rect):
        """Handle clicks on volume sliders"""
        if bgm_rect.collidepoint(mouseX, mouseY):
            # Calculate new BGM volume based on click position
            relative_x = mouseX - bgm_rect.x
            new_volume = relative_x / bgm_rect.width
            self.soundEffect.set_bgm_volume(new_volume)
            # Play a test sound
            self.soundEffect.playHitSound()
            return True
        elif sfx_rect.collidepoint(mouseX, mouseY):
            # Calculate new SFX volume based on click position
            relative_x = mouseX - sfx_rect.x
            new_volume = relative_x / sfx_rect.width
            self.soundEffect.set_sfx_volume(new_volume)
            # Play a test sound
            self.soundEffect.playHitSound()
            return True
        return False

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
            
            # Draw volume sliders
            bgm_rect, sfx_rect = self.draw_volume_sliders(mouseX, mouseY)
                
            # Draw instruction guide
            instructions = [
                "CONTROLS",
                "Mouse - Click to whack zombies",
                "P - Pause/Resume game",
                "F - Toggle FPS display",
                "A - Toggle Accuracy display", 
                "M - Toggle Mute/Unmute sound"
            ]
            
            start_y = 450  # Position below the start button
            instruction_font = pygame.font.Font(Constants.FONT_NAME, 20)
            
            for i, instruction in enumerate(instructions):
                if i == 0:  # Title
                    color = (255, 255, 100)  # Yellow for title
                    font_to_use = pygame.font.Font(Constants.FONT_NAME, 24)
                else:
                    color = (200, 200, 200)  # Light gray for instructions
                    font_to_use = instruction_font
                    
                instruction_text = font_to_use.render(instruction, True, color)
                instruction_rect = instruction_text.get_rect(center=(Constants.SCREEN_WIDTH // 2, start_y + i * 25))
                self.screen.blit(instruction_text, instruction_rect)
                
            pygame.display.update()
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Check volume slider clicks first
                    if self.handle_volume_slider_click(mouseX, mouseY, bgm_rect, sfx_rect):
                        continue  # Volume slider was clicked, don't start game
                    # Check start button
                    elif mouseX >= 527 and mouseX <= 794 and mouseY >= 352 and mouseY <= 406:
                        gameStart = True
                elif event.type == pygame.QUIT:
                    pygame.quit()

        # Game settings
        loop = True
        mouse.set_visible(False)

        # Flag variables
        isClicked = False
        isEaten = False

        # Time variables
        clock = pygame.time.Clock()
        cycle_time = 0
        gameTime = 0
        lastSpawnTime = 0

        # Zombie-spawning variables
        maxStayTime = 5
        respawnTime = 1.5
        hitPos = -1

        while loop:
            if self.brains > 0:
                # Calculate game input
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        loop = False
                    elif event.type == KEYDOWN:
                        # Handle HUD toggles
                        if event.key == K_f:
                            self.show_fps = not self.show_fps
                        elif event.key == K_a:
                            self.show_accuracy = not self.show_accuracy
                        elif event.key == K_m:
                            self.soundEffect.toggleMute()
                        elif event.key == K_p:
                            self.paused = not self.paused
                    elif event.type == MOUSEBUTTONDOWN and event.button == Constants.LEFT_MOUSE_BUTTON and not self.paused:
                        # Pygame event system naturally prevents double-counting
                        isClicked = True
                        self.total_shots += 1
                        hitPos = self.isZombieHit(mouse.get_pos())
                        if hitPos != -1:
                            # Hit a zombie - increment hits counter
                            self.hits += 1
                            zombie_killed = self.hit_zombie(hitPos)
                            if zombie_killed:
                                # Zombie was killed - increment kills counter
                                self.kills += 1
                                self.level = self.getPlayerLevel()
                                maxStayTime = self.getStayTime()
                                respawnTime = self.getRespawnTime()
                        else:
                            # Missed completely
                            self.misses += 1
                            self.soundEffect.playMissSound()
                    else:
                        isClicked = False

                # Calculate game time (but freeze if paused)
                mil = clock.tick(Constants.FPS)
                if not self.paused:
                    sec = mil / 1000.0
                    cycle_time += sec
                    gameTime += sec
                    
                    # Update effects only if not paused
                    self.screen_effects.update(sec)
                    self.particle_system.update(sec)
                else:
                    sec = 0  # Freeze time when paused

                # Calculate zombies' variables (only if not paused)
                zombieIndex = 0
                while zombieIndex < self.zombie_count:
                    thisZombie = self.zombie[zombieIndex]
                    thisZombie.stayTime += sec

                    # Zombie status: rise
                    if thisZombie.zombieStatus == 0:
                        if thisZombie.stayTime > Constants.SPAWN_ANI_TIME:
                            if thisZombie.animationIndex > Constants.SPAWN_ANI_INDEX_MAX:
                                if thisZombie.stayTime > maxStayTime:
                                    thisZombie.animationIndex = Constants.SPAWN_ANI_INDEX_MAX
                                    thisZombie.zombieStatus = 1  # Start attacking
                                    thisZombie.stayTime = 0
                                    thisZombie.attack_timer = 0
                                    thisZombie.attack_animation_index = 0
                                    continue
                            else:
                                thisZombie.pic = self.zombie_image[thisZombie.animationIndex]
                                thisZombie.animationIndex += 1
                                thisZombie.stayTime = 0

                    # Zombie status: attacking (new enhanced attack sequence)
                    elif thisZombie.zombieStatus == 1:
                        thisZombie.attack_timer += sec
                        if thisZombie.attack_timer > Constants.ATTACK_ANI_TIME:
                            if thisZombie.attack_animation_index < len(self.zombie_attack_frames):
                                thisZombie.pic = self.zombie_attack_frames[thisZombie.attack_animation_index]
                                thisZombie.attack_animation_index += 1
                                thisZombie.attack_timer = 0
                            else:
                                # Attack complete - process attack and start escaping
                                self.process_zombie_attack(thisZombie)
                                thisZombie.zombieStatus = 3  # Escaping
                                thisZombie.animationIndex = Constants.SPAWN_ANI_INDEX_MAX
                                thisZombie.stayTime = 0
                                isEaten = True

                    # Zombie status: dead
                    elif thisZombie.zombieStatus == 2:
                        if thisZombie.stayTime > Constants.DEAD_ANI_TIME:
                            if thisZombie.animationIndex < Constants.DEAD_ANI_INDEX_MAX:
                                thisZombie.pic = self.zombie_image[thisZombie.animationIndex]
                            thisZombie.animationIndex += 1
                            thisZombie.stayTime = 0
                            if thisZombie.animationIndex > Constants.DEAD_ANI_INDEX_MAX:
                                self.zombie.pop(zombieIndex)
                                self.zombie_count -= 1
                                continue

                    # Zombie status: escaping (after attack)
                    elif thisZombie.zombieStatus == 3:
                        if thisZombie.stayTime > Constants.SPAWN_ANI_TIME:
                            if thisZombie.animationIndex >= 0:
                                thisZombie.pic = self.zombie_image[thisZombie.animationIndex]
                            thisZombie.animationIndex -= 1
                            thisZombie.stayTime = 0
                            if thisZombie.animationIndex < -1:
                                self.zombie.pop(zombieIndex)
                                self.zombie_count -= 1
                                continue

                    zombieIndex += 1

                # Update display
                self.update_sprite()
                
                # Draw particles
                self.particle_system.draw(self.screen)
                
                # Draw screen effects
                self.screen_effects.draw_blood_overlay(self.screen)
                self.screen_effects.draw_damage_indicators(self.screen, self.small_font)
                
                # Update HUD
                current_fps = clock.get_fps()
                self.update_hud(current_fps)
                self.update_statistics(isClicked, isEaten)
                
                # Spawn new zombies (only if not paused)
                if not self.paused and gameTime - lastSpawnTime > respawnTime:
                    if self.generateZombie():
                        lastSpawnTime = gameTime

                # Show pause overlay if paused
                if self.paused:
                    # Dim the background
                    pause_surface = pygame.Surface((Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT))
                    pause_surface.set_alpha(128)
                    pause_surface.fill((0, 0, 0))
                    self.screen.blit(pause_surface, (0, 0))
                    
                    # Draw pause symbol (||)
                    pause_font = pygame.font.Font(Constants.FONT_NAME, 120)
                    pause_text = pause_font.render("PAUSED", True, (255, 255, 255))
                    pause_rect = pause_text.get_rect(center=(Constants.SCREEN_WIDTH//2, Constants.SCREEN_HEIGHT//2 - 30))
                    self.screen.blit(pause_text, pause_rect)
                    
                    # Show instruction
                    instruction_text = self.small_font.render("Press P to Resume", True, (200, 200, 200))
                    instruction_rect = instruction_text.get_rect(center=(Constants.SCREEN_WIDTH//2, Constants.SCREEN_HEIGHT//2 + 60))
                    self.screen.blit(instruction_text, instruction_rect)

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
                            # Reset game
                            self.brains = 3
                            self.hits = 0
                            self.kills = 0
                            self.misses = 0
                            self.level = 1
                            self.zombie_count = 0
                            self.total_shots = 0
                            self.zombie = []
                            self.screen_effects = ScreenEffect()
                            self.particle_system = ParticleSystem()
                            self.fps_samples = []
                            
                            clock = pygame.time.Clock()
                            cycle_time = 0
                            gameTime = 0
                            lastSpawnTime = 0
                            maxStayTime = 5
                            respawnTime = 1.5
                            hitPos = -1
                            mouse.set_visible(False)

            pygame.display.update()

###########################################################################
# Initialize the game
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
pygame.init()

myGame = Game()
myGame.start()

pygame.quit()
