import argparse
import sys
import depthai as dai
import spectacularAI
import pygame

# --- Pygame Configuration ---
WIDTH, HEIGHT = 800, 800
BG_COLOR = (30, 30, 30)
TEXT_COLOR = (240, 240, 240)
TRAJ_COLOR = (0, 255, 150)
POINT_COLOR = (255, 50, 50)
SCALE = 150.0  # Pixels per meter for the top-down view

def draw_text(screen, font, text, x, y, color=TEXT_COLOR):
    surface = font.render(text, True, color)
    screen.blit(surface, (x, y))

def main():
    parser = argparse.ArgumentParser(description="SpectacularAI Mapping with Pygame GUI")
    parser.add_argument('--map_location', type=str, default='map.bin', help="Path to save the binary map file")
    parser.add_argument('--mp4', type=str, help="Path to save the RGB video (raw h264 stream)")
    args = parser.parse_args()

    # 1. Initialize Pygame
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("SpectacularAI SLAM Tracker")
    font = pygame.font.SysFont(None, 32)
    clock = pygame.time.Clock()

    # 2. Configure DepthAI and SpectacularAI
    pipeline = dai.Pipeline()
    config = spectacularAI.depthai.Configuration()
    config.useSlam = True
    config.mapSavePath = args.map_location
    
    if args.mp4:
        config.useColor = True

    vio_pipeline = spectacularAI.depthai.Pipeline(pipeline, config)

    # 3. Setup hardware-accelerated video encoding on the OAK-D
    if args.mp4:
        # FIX: Force the camera to Planar mode so SpectacularAI doesn't crash with RGB888i
        vio_pipeline.color.setInterleaved(False)
        vio_pipeline.color.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

        video_enc = pipeline.create(dai.node.VideoEncoder)
        video_enc.setDefaultProfilePreset(30, dai.VideoEncoderProperties.Profile.H264_MAIN)

        # FIX: Link the 'isp' output instead of 'video' for better encoder compatibility
        vio_pipeline.color.isp.link(video_enc.input)

        xout_video = pipeline.create(dai.node.XLinkOut)
        xout_video.setStreamName("video_out")
        video_enc.bitstream.link(xout_video.input)

    trajectory = []
    state = "WAITING"  # States: WAITING, MAPPING, QUIT
    vio_session = None
    video_queue = None
    video_file = None

    print("Initializing OAK-D device...")

    # 4. Main Application Loop
    with dai.Device(pipeline) as device:
        while state != "QUIT":
            screen.fill(BG_COLOR)

            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    state = "QUIT"
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_s and state == "WAITING":
                        print("Mapping started.")
                        state = "MAPPING"
                        # Start the session only when 's' is pressed
                        vio_session = vio_pipeline.startSession(device)

                        if args.mp4:
                            video_queue = device.getOutputQueue(name="video_out", maxSize=30, blocking=False)
                            # Clear old frames that buffered before 's' was pressed
                            video_queue.getAll()
                            video_file = open(args.mp4, 'wb')
                            print(f"Recording video to {args.mp4}")
                            
                    elif event.key == pygame.K_q:
                        state = "QUIT"

            # State Logic & Rendering
            if state == "WAITING":
                draw_text(screen, font, "READY TO MAP", 20, 20)
                draw_text(screen, font, f"Map will be saved to: {args.map_location}", 20, 60)
                draw_text(screen, font, "[S] - Start Mapping", 20, 120, (100, 255, 100))
                draw_text(screen, font, "[Q] - Quit", 20, 160, (255, 100, 100))

            elif state == "MAPPING" and vio_session is not None:
                # Fetch tracking data
                if vio_session.hasOutput():
                    out = vio_session.getOutput()
                    
                    # OAK-D standard coordinates: X is right, Y is down, Z is forward.
                    # For a top-down view, we map X to screen X, and Z to screen Y.
                    px = int(WIDTH / 2 + out.pose.position.x * SCALE)
                    py = int(HEIGHT / 2 - out.pose.position.z * SCALE)
                    
                    # Only add point if it moved a bit (prevents rendering too many stacked points)
                    if not trajectory or (abs(trajectory[-1][0] - px) > 1 or abs(trajectory[-1][1] - py) > 1):
                        trajectory.append((px, py))

                # Fetch and save encoded video frames
                if args.mp4 and video_queue is not None and video_queue.has():
                    while video_queue.has():
                        video_packet = video_queue.get()
                        video_packet.getData().tofile(video_file)

                # UI Overlay
                draw_text(screen, font, "MAPPING IN PROGRESS (● REC)", 20, 20, (255, 50, 50))
                draw_text(screen, font, f"Tracked Poses: {len(trajectory)}", 20, 60)
                draw_text(screen, font, "[Q] - Stop & Save Map", 20, 100)

                # Draw the camera trajectory
                if len(trajectory) > 1:
                    pygame.draw.lines(screen, TRAJ_COLOR, False, trajectory, 2)
                
                # Draw current position indicator
                if trajectory:
                    pygame.draw.circle(screen, POINT_COLOR, trajectory[-1], 6)

            pygame.display.flip()
            
            # Cap framerate to 60 FPS to avoid burning CPU
            clock.tick(60)

    # 5. Cleanup and Serialization
    print("\nShutting down...")
    if vio_session:
        print(f"Serializing map to {args.map_location}...")
        vio_session.close() # Explicitly closing triggers the map save
        
    if video_file:
        video_file.close()
        print(f"Video saved to {args.mp4}")
        
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
