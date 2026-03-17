import pygame
import os


pygame.init()
pygame.joystick.init()

class Dualsense: 
    def __init__(self):
        os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
        self.joysticks = {}
        self.connect_joysticks()
        self.ps5_triggers = {
            "l2": 4,
            "r2": 5
        }
        self.ps5_dualsense_button_combo = {
            "cross": 0,
            "circle": 1,
            "square": 2,
            "triangle": 3,
            "create": 4,     # Previously glow_button
            "ps_button": 5,  # Official Sony name for the logo button
            "options": 6,    # Previously menu
            "l3": 7,         # Left stick click
            "r3": 8,         # Right stick click
            "l1": 9,
            "r1": 10,
            "dpad_up": 11,
            "dpad_down": 12,
            "dpad_left": 13,
            "dpad_right": 14,
            "touchpad": 15,  # Center pad click
            "mute": 16
        }

    def connect_joysticks(self):
        for i in range(pygame.joystick.get_count()):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()
            self.joysticks[joystick.get_instance_id()] = joystick
            print(f"Connected joystick: {joystick.get_name()} (ID: {joystick.get_instance_id()})")

    def disconnect_joystick(self, joystick_id):
        if joystick_id in self.joysticks:
            print(f"Disconnected joystick: {self.joysticks[joystick_id].get_name()} (ID: {joystick_id})")
            del self.joysticks[joystick_id]

    def handle_event(self, event):
        if event.type == pygame.JOYDEVICEADDED:
            self.connect_joysticks()
        elif event.type == pygame.JOYDEVICEREMOVED:
            self.disconnect_joystick(event.instance_id)

    def get_axis(self, index, stick) -> tuple[float, float]:
        deadzone = 0.15  # Ignore anything less than 15% tilt
        try:
            if index in self.joysticks:
                joy = self.joysticks[index]
                # Get raw values
                raw_x = joy.get_axis(0 if stick.lower() == "left" else 2)
                raw_y = joy.get_axis(1 if stick.lower() == "left" else 3)
                
                # Apply deadzone
                x = raw_x if abs(raw_x) > deadzone else 0.0
                y = raw_y if abs(raw_y) > deadzone else 0.0
                return (x, y)
            return (0, 0)
        except:
            return (0, 0)
    def get_trigger(self, index, trigger: str) -> float:
        """
        Returns the trigger value. 
        Raw Pygame value: -1.0 (released) to 1.0 (pressed).
        Mapped value: 0.0 (released) to 1.0 (pressed).
        """
        try:
            if index in self.joysticks:
                axis_id = self.ps5_triggers[trigger.lower()]
                raw_value = self.joysticks[index].get_axis(axis_id)
                
                # Convert from (-1 to 1) to (0 to 1)
                normalized = (raw_value + 1) / 2
                return round(normalized, 3)
            return 0.0
        except (KeyError, IndexError):
            return 0.0


    def get_button(self, button:str, index = 0) -> bool:
        try:
            # Check if the joystick is in our dictionary and return its button state
            if index in self.joysticks:
                return bool(self.joysticks[index].get_button(self.ps5_dualsense_button_combo[button.lower()]))
            return False
        except (IndexError, pygame.error):
            # Return False if the button number or joystick is invalid
            return False

    def get_hat(self, joystick_id, hat_id):
        if joystick_id in self.joysticks:
            return self.joysticks[joystick_id].get_hat(hat_id)
        return (0, 0)

    def get_num_joysticks(self):
        return len(self.joysticks)

    def get_joystick_names(self):
        return {id: joy.get_name() for id, joy in self.joysticks.items()}

if __name__ == '__main__':
    controller = Dualsense()
    b = None
    while True:
        os.system("cls")

        # 1. Process all events to update the internal state
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit()
                exit()
            if e.type == pygame.JOYBUTTONDOWN:
                b = e.button
            
            controller.handle_event(e)
           
        if controller.get_button("cross"): pygame.quit(); exit()
        # 2. Print values every frame (OUTSIDE the event loop)
        # Using controller.joysticks.keys() ensures you query active IDs
        print(f"Button {b} pressed")
        print(f"Left Stick: {controller.get_axis(0,"left")}")
        print(f"Right Stick: {controller.get_axis(0,"Right")}")
        print(f"Left Trigger: {controller.get_trigger(0,'l2')}")
        print(f"Right Trigger: {controller.get_trigger(0,'r2')}")


