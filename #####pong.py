import pygame
import sys
import random
import numpy as np

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PADDLE_WIDTH = 100
PADDLE_HEIGHT = 10
BALL_SIZE = 10
BRICK_WIDTH = 80
BRICK_HEIGHT = 30
BRICK_ROWS = 5
BRICK_COLS = 10
FPS = 60

# Colors (Famicom-inspired palette)
WHITE = (255, 248, 208)  # Famicom white-ish
BLACK = (0, 0, 0)       # Background
RED = (255, 40, 32)     # Ball (NES red)
BLUE = (40, 80, 255)    # Paddle (NES blue)
BRICK_COLORS = [(255, 40, 32), (40, 255, 80), (255, 168, 40)]  # Red, Green, Orange

# Set up the screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Breakout - Famicom Style")
clock = pygame.time.Clock()

# Font for game over text
font = pygame.font.Font(None, 74)

# Sound effects (GBA-style square wave)
def create_gba_sound(freq=440, duration=0.1, duty_cycle=0.25):
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = np.sign(np.sin(2 * np.pi * freq * t)) * (t < duration * duty_cycle)
    wave = wave * 0.3
    stereo = np.column_stack((wave, wave)).astype(np.float32)
    return pygame.sndarray.make_sound(stereo)

beep_paddle = create_gba_sound(523.25, 0.08, 0.125)  # C5 note, short pulse
boop_brick = create_gba_sound(783.99, 0.12, 0.25)   # G5 note, medium pulse
lose_sound = create_gba_sound(261.63, 0.2, 0.5)     # C4 note, longer pulse

# Paddle setup
def reset_game():
    global paddle, ball, ball_speed, bricks
    paddle = pygame.Rect(SCREEN_WIDTH // 2 - PADDLE_WIDTH // 2, SCREEN_HEIGHT - 40, PADDLE_WIDTH, PADDLE_HEIGHT)
    ball = pygame.Rect(SCREEN_WIDTH // 2 - BALL_SIZE // 2, SCREEN_HEIGHT // 2 - BALL_SIZE // 2, BALL_SIZE, BALL_SIZE)
    ball_speed = [5, -5]
    bricks = []
    for row in range(BRICK_ROWS):
        for col in range(BRICK_COLS):
            brick = pygame.Rect(col * (BRICK_WIDTH + 5) + 35, row * (BRICK_HEIGHT + 5) + 50, BRICK_WIDTH, BRICK_HEIGHT)
            bricks.append((brick, BRICK_COLORS[row % len(BRICK_COLORS)]))

# Initial game setup
reset_game()

# Game loop
def main():
    game_over = False
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if game_over and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    reset_game()
                    game_over = False
                elif event.key == pygame.K_n:
                    pygame.quit()
                    sys.exit()

        if not game_over:
            # Mouse controls for paddle
            mouse_x = pygame.mouse.get_pos()[0]
            paddle.centerx = mouse_x
            if paddle.left < 0:
                paddle.left = 0
            if paddle.right > SCREEN_WIDTH:
                paddle.right = SCREEN_WIDTH

            # Ball movement
            ball.x += ball_speed[0]
            ball.y += ball_speed[1]

            # Ball collisions with walls
            if ball.left <= 0 or ball.right >= SCREEN_WIDTH:
                ball_speed[0] = -ball_speed[0]
                beep_paddle.play()
            if ball.top <= 0:
                ball_speed[1] = -ball_speed[1]
                beep_paddle.play()
            if ball.bottom >= SCREEN_HEIGHT:
                lose_sound.play()
                ball.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                ball_speed[0] = random.choice([5, -5])
                ball_speed[1] = -5

            # Ball collision with paddle
            if ball.colliderect(paddle):
                ball_speed[1] = -ball_speed[1]
                hit_pos = (ball.centerx - paddle.centerx) / (PADDLE_WIDTH / 2)
                ball_speed[0] += hit_pos * 2
                beep_paddle.play()

            # Ball collision with bricks
            for brick, _ in bricks[:]:
                if ball.colliderect(brick):
                    bricks.remove((brick, _))
                    ball_speed[1] = -ball_speed[1]
                    boop_brick.play()
                    break

            # Check for game over (all bricks cleared)
            if not bricks:
                game_over = True

        # Draw everything
        screen.fill(BLACK)
        if game_over:
            game_over_text = font.render("GAME OVER", True, WHITE)
            prompt_text = font.render("Restart? (Y/N)", True, WHITE)
            screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
            screen.blit(prompt_text, (SCREEN_WIDTH // 2 - prompt_text.get_width() // 2, SCREEN_HEIGHT // 2 + 50))
        else:
            pygame.draw.rect(screen, BLUE, paddle, 0, 2)
            pygame.draw.rect(screen, RED, ball, 0, 2)
            for brick, color in bricks:
                pygame.draw.rect(screen, color, brick, 0, 2)

        # Update display and maintain 60 FPS
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
