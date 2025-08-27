# Sound effects

import pygame
import os
from pygame import *
from Classes.GameDefine import SoundConstants

class SoundEffect:
    def __init__(self):
        self.muted = False
        
        # Volume settings (0.0 to 1.0)
        self.bgm_volume = 0.7  # Background music volume
        self.sfx_volume = 0.8  # Sound effects volume
        
        # Load background music
        self.bgMusic = pygame.mixer.music.load(SoundConstants.SOUND_BG)
        pygame.mixer.music.set_volume(self.bgm_volume)
        
        # Load sound effects
        self.hitSound = pygame.mixer.Sound(SoundConstants.SOUND_HIT)
        self.missSound = pygame.mixer.Sound(SoundConstants.SOUND_MISS)
        self.levelUpSound = pygame.mixer.Sound(SoundConstants.SOUND_LEVEL_UP)
        
        # Set initial volume for sound effects
        self.hitSound.set_volume(self.sfx_volume)
        self.missSound.set_volume(self.sfx_volume)
        self.levelUpSound.set_volume(self.sfx_volume)
        
        # Store all sound effects for volume control
        self.all_sounds = [self.hitSound, self.missSound, self.levelUpSound]
        
        # Load new sounds if they exist, otherwise use existing sounds as placeholders
        try:
            if os.path.exists(SoundConstants.SOUND_ZOMBIE_ATTACK):
                self.zombieAttackSound = pygame.mixer.Sound(SoundConstants.SOUND_ZOMBIE_ATTACK)
            else:
                self.zombieAttackSound = self.hitSound  # Placeholder
        except:
            self.zombieAttackSound = self.hitSound
            
        try:
            if os.path.exists(SoundConstants.SOUND_ZOMBIE_HURT):
                self.zombieHurtSound = pygame.mixer.Sound(SoundConstants.SOUND_ZOMBIE_HURT)
            else:
                self.zombieHurtSound = self.hitSound  # Placeholder
        except:
            self.zombieHurtSound = self.hitSound
            
        try:
            if os.path.exists(SoundConstants.SOUND_PLAYER_HURT):
                self.playerHurtSound = pygame.mixer.Sound(SoundConstants.SOUND_PLAYER_HURT)
            else:
                self.playerHurtSound = self.missSound  # Placeholder
        except:
            self.playerHurtSound = self.missSound
            
        try:
            if os.path.exists(SoundConstants.SOUND_PLAYER_DEATH):
                self.playerDeathSound = pygame.mixer.Sound(SoundConstants.SOUND_PLAYER_DEATH)
            else:
                self.playerDeathSound = self.missSound  # Placeholder
        except:
            self.playerDeathSound = self.missSound
            
        # Add new sounds to the all_sounds list and set their volume
        if self.zombieAttackSound not in self.all_sounds:
            self.all_sounds.append(self.zombieAttackSound)
            self.zombieAttackSound.set_volume(self.sfx_volume)
            
        if self.zombieHurtSound not in self.all_sounds:
            self.all_sounds.append(self.zombieHurtSound)
            self.zombieHurtSound.set_volume(self.sfx_volume)
            
        if self.playerHurtSound not in self.all_sounds:
            self.all_sounds.append(self.playerHurtSound)
            self.playerHurtSound.set_volume(self.sfx_volume)
            
        if self.playerDeathSound not in self.all_sounds:
            self.all_sounds.append(self.playerDeathSound)
            self.playerDeathSound.set_volume(self.sfx_volume)
            
        pygame.mixer.music.play(-1)

    def toggleMute(self):
        self.muted = not self.muted
        if self.muted:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()

    def playHitSound(self):
        if not self.muted:
            self.hitSound.play()

    def playMissSound(self):
        if not self.muted:
            self.missSound.play()

    def playLevelUpSound(self):
        if not self.muted:
            self.levelUpSound.play()
            
    def playZombieAttackSound(self):
        if not self.muted:
            self.zombieAttackSound.play()
            
    def playZombieHurtSound(self):
        if not self.muted:
            self.zombieHurtSound.play()
            
    def playPlayerHurtSound(self):
        if not self.muted:
            self.playerHurtSound.play()
            
    def playPlayerDeathSound(self):
        if not self.muted:
            self.playerDeathSound.play()
    
    def set_bgm_volume(self, volume):
        """Set background music volume (0.0 to 1.0)"""
        self.bgm_volume = max(0.0, min(1.0, volume))  # Clamp between 0 and 1
        pygame.mixer.music.set_volume(self.bgm_volume)
    
    def set_sfx_volume(self, volume):
        """Set sound effects volume (0.0 to 1.0)"""
        self.sfx_volume = max(0.0, min(1.0, volume))  # Clamp between 0 and 1
        for sound in self.all_sounds:
            sound.set_volume(self.sfx_volume)
    
    def get_bgm_volume(self):
        """Get current background music volume"""
        return self.bgm_volume
    
    def get_sfx_volume(self):
        """Get current sound effects volume"""
        return self.sfx_volume
