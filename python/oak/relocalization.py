import argparse
import sys
import depthai as dai
import spectacularAI
import pygame

# --- Pygame Configuration ---
WIDTH, HEIGHT = 800, 800
BG_COLOR = (30, 30, 40)
TEXT_COLOR = (240, 240, 240)
TRAJ_COLOR = (100, 200, 255)
POINT_COLOR = (50, 255, 50)
WARNING_COLOR = (255, 150, 50)
SCALE = 150.0  # Pixels per meter

def draw_text(screen, font, text, x, y, color=TEXT_COLOR):
    surface = font.render(text, True, color)
    screen.blit(surface, (x, y))

def main():
    parser = argparse.ArgumentParser(description="SpectacularAI Relocalization with Pygame GUI")
    parser.add_argument('--map_location', type=str, required=True, help="Path to the existing binary map file to load (e.g., map.bin)")
    args = parser.parse_args()

    # 1. Initialize Pygame
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("SpectacularAI Relocalization")
    font = pygame.font.SysFont(None, 32)
    clock = pygame.time.Clock()

    # 2. Configure DepthAI and SpectacularAI
    pipeline = dai.Pipeline()
    config = spectacularAI.depthai.Configuration()
    config.useSlam = True
    
    # LOAD the existing map for relocalization
    config.mapLoadPath = args.map_location

    vio_pipeline = spectacularAI.depthai.Pipeline(pipeline, config)

    trajectory = []
    state = "WAITING"  # States: WAITING, TRACKING, QUIT
    vio_session = None

    print("Initializing OAK-D device...")
    
    # 3. Main Application Loop
    with dai.Device(pipeline) as device:
        while state != "QUIT":
            screen.fill(BG_COLOR)

            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    state = "QUIT"
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_s and state == "WAITING":
                        print(f"Loading map from {args.map_location} and starting session...")
                        state = "TRACKING"
                        vio_session = vio_pipeline.startSession(device)
                    elif event.key == pygame.K_q:
                        state = "QUIT"

            # State Logic & Rendering
            if state == "WAITING":
                draw_text(screen, font, "READY TO RELOCALIZE", 20, 20)
                draw_text(screen, font, f"Will load map: {args.map_location}", 20, 60)
                draw_text(screen, font, "[S] - Start Relocalization", 20, 120, (100, 255, 100))
                draw_text(screen, font, "[Q] - Quit", 20, 160, (255, 100, 100))

            elif state == "TRACKING" and vio_session is not None:
                tracking_status_str = "UNKNOWN"
                
                # Fetch tracking data
                if vio_session.hasOutput():
                    out = vio_session.getOutput()
                    
                    # Map Enum to string for display
                    if out.status == spectacularAI.TrackingStatus.TRACKING:
                        tracking_status_str = "TRACKING (Map Aligned)"
                        status_color = POINT_COLOR
                    elif out.status == spectacularAI.TrackingStatus.INIT:
                        tracking_status_str = "INITIALIZING..."
                        status_color = WARNING_COLOR
                    else:
                        tracking_status_str = "LOST"
                        status_color = (255, 50, 50)
                    
                    # Convert to Pygame coordinates (X is right, Z is forward)
                    px = int(WIDTH / 2 + out.pose.position.x * SCALE)
                    py = int(HEIGHT / 2 - out.pose.position.z * SCALE)
                    
                    # Append if moved
                    if not trajectory or (abs(trajectory[-1][0] - px) > 1 or abs(trajectory[-1][1] - py) > 1):
                        trajectory.append((px, py))

                # UI Overlay
                draw_text(screen, font, f"STATUS: {tracking_status_str}", 20, 20, status_color)
                draw_text(screen, font, "[Q] - Stop & Exit", 20, 60)

                # Draw the camera trajectory in the map's coordinate space
                if len(trajectory) > 1:
                    pygame.draw.lines(screen, TRAJ_COLOR, False, trajectory, 2)
                
                # Draw current position indicator
                if trajectory:
                    pygame.draw.circle(screen, status_color, trajectory[-1], 8)

            pygame.display.flip()
            clock.tick(60)

    # 4. Cleanup
    print("\nShutting down...")
    if vio_session:
        vio_session.close()
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
