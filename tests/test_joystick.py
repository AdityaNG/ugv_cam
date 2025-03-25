import pygame

# Initialize pygame
pygame.init()

# Specifically initialize the joystick module
pygame.joystick.init()

# Get the number of joysticks/game controllers
joystick_count = pygame.joystick.get_count()
print(f"Number of joysticks: {joystick_count}")

# Initialize each joystick
for i in range(joystick_count):
    joystick = pygame.joystick.Joystick(i)
    joystick.init()
    
    # Print joystick information
    print(f"Joystick {i}")
    print(f"Joystick name: {joystick.get_name()}")
    print(f"Number of axes: {joystick.get_numaxes()}")
    print(f"Number of buttons: {joystick.get_numbuttons()}")
    print(f"Number of hats: {joystick.get_numhats()}")

# Keep the program running to test joystick
try:
    while True:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            
            # Print joystick events
            elif event.type == pygame.JOYBUTTONDOWN:
                print(f"Button {event.button} pressed on joystick {event.joy}")
            elif event.type == pygame.JOYAXISMOTION:
                print(f"Axis {event.axis} moved to {event.value} on joystick {event.joy}")

except KeyboardInterrupt:
    pygame.quit()