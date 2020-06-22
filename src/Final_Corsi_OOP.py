# -*- coding: utf-8 -*-
"""
Created on Sun Mar 22 11:08:34 2020

@author: ilste
"""

import pygame
import sys
from pygame.locals import *
import pygame_textinput
from math import sqrt
import random
from time import time
import csv

# --------------------------- Set Parameters Here -----------------------------
# Set application size
SCREEN_SIZE = (800, 600)

# Set maximum number of participants
MAX_PARTICIPANTS = 20

# Set maximum number of trials per participant
MAX_TRIALS = 3

# Set time until first box is highlighted after instructions
START_DELAY = 1.0  # s

# Set box parameters
N_BOXES = 9  # number of boxes
BOX_SIZE = 50  # side length of boxes in pixels
MARGIN = 1.5 * BOX_SIZE  # free margin at the borders of the screen
MIN_DIST = 2.0 * BOX_SIZE  # minimum distance between the centers of two boxes
HIGHLIGHT_TIME = 1.0  # highlight duration for each box during
# sequence presentation in s

BOX_PARAMS = {'n_boxes': N_BOXES, 'size': BOX_SIZE, 'min_dist': MIN_DIST,
              't_highlight': HIGHLIGHT_TIME, 'margin': MARGIN}


# -----------------------------------------------------------------------------


class Participant:
    def __init__(self, participant_id):
        """
        Participant class to handle all attributes of the participant and
        statistics about their performance.
        :param participant_id: unique participant ID
        """

        self.participant_id = participant_id

        # Current trial
        self.current_trial = 1

        # Store participant's corsi spans for all trials
        self.corsi_spans = []

        # Corsi span in current trial
        self.corsi_span = 2

        # Clicks made in current sequence
        # Use to check correctness of user input
        self.clicks = 0

        # Errors made by user
        # Two errors for same sequence length will terminate trial
        self.errors = 0

        # Keep track of performance statistics
        self.mean_corsi_span = 0
        self.std_corsi_span = 0

    def update_statistics(self):
        """
        Update participant statistics after each trial.
        """

        # Append current corsi span to list of corsi spans if current
        # corsi span not yet added
        if len(self.corsi_spans) < self.current_trial:
            self.corsi_spans.append(self.corsi_span)

        # Compute mean and standard deviation
        self.mean_corsi_span = round(sum(self.corsi_spans) /
                                     len(self.corsi_spans), 2)
        self.std_corsi_span = round(sqrt(sum((xi - self.mean_corsi_span) ** 2
                                       for xi in self.corsi_spans) /
                                   len(self.corsi_spans)), 2)

    def write_csv(self):
        """
        Write participant's results to CSV file at the end of the experiment.
        """
        with open("corsi.csv", "a") as database:
            # Write results to csv file
            # Format: ID, number of attempts, mean, std
            writer = csv.writer(database)
            writer.writerow([self.participant_id, self.corsi_spans,
                             self.mean_corsi_span, self.std_corsi_span])


class Sequence:

    # Declare box as member class of sequence class
    class Box:

        # Declare colors as static member variables of box class
        RED, GREEN = (255, 0, 0), (0, 255, 0)
        BLUE, YELLOW = (0, 0, 255), (255, 255, 0)

        def __init__(self, pos, size):
            """
            Class Box: For the box properties that are used, a class is
            written
            to avoid duplicate code. This can be done because all box
            instances
            have the same properties.
            :param pos: tuple (int, int) | center coordinates of box
            :param size: int | side length of rectangular box
            """

            self.pos = pos
            self.size = size

            # Flag to highlight box during drawing of sequence
            self.highlight = False

            # Flag to mark box as clicked during user input
            self.clicked = False

            # Flag to mark if box was correctly clicked by user
            self.correct = False

            # Declare variables used for drawing the box
            self.rend = None
            self.rect = None

        def get_color(self):
            """
            Set box color based on flags.
            """

            # Highlighted box will be displayed in yellow
            if self.highlight:
                return self.YELLOW

            # Clicked box will be displayed in green if correct and red
            # if false
            elif self.clicked:
                if self.correct:
                    return self.GREEN
                else:
                    return self.RED

            # Box without flags will be displayed in blue
            else:
                return self.BLUE

        def draw(self, screen):
            """
            Draw box on screen
            :param screen: PyGame screen object
            """

            # Get PyGame surface of box size
            self.rend = pygame.Surface((self.size, self.size))

            # Assign box location to surface
            self.rect = self.rend.get_rect(center=self.pos)

            # Set box color
            self.rend.fill(self.get_color())

            # Display box
            screen.blit(self.rend, self.rect)

    def __init__(self, screen_size, box_parameters):
        """
        Sequence class to handle the display sequence. Contains a list of
        boxes and all functions relevant for displaying the boxes.
        :param screen_size: tuple (int, int) | width and height of
        application
        :param box_parameters: dict of box parameters
        """

        self.screen_size = screen_size
        self.box_parameters = box_parameters

        # Set initial sequence length to None. Will be updated every time a
        # new sequence is generated
        self.length = None

        # Set index of current box to be highlighted in display function
        self.highlight_box_id = 0

        # Set time when last box was highlighted. Necessary to maintain
        # interval between highlighted boxes
        self.last_box_highlighted = 0

        # Initialize empty list of boxes. Will be updated every time a new
        # sequence is generated
        self.boxes = []

        # Flag to indicate if user input for sequence was correct
        self.correct = False

    def generate(self, length):
        """
        Generate a new sequence of given length.
        :param length: int | length of sequence
        """

        # Set sequence length
        self.length = length

        # Generate random boxes
        self.boxes = self.generate_boxes()

        # Set first box as highlighted box
        self.highlight_box_id = 0

    def generate_boxes(self):
        """
        Generate a list of randomly placed, non-overlapping box objects.
        """

        # Get free margin at the borders of the screen
        margin = self.box_parameters['margin']

        # Initialize empty list
        boxes = []

        # Set number of generated boxes to 0
        i = 0

        # Loop until specified number of non-overlapping boxes is reached
        while i < self.box_parameters['n_boxes']:

            # Sample random x and y position on screen
            random_x = random.randint(margin, self.screen_size[0] - margin)
            random_y = random.randint(margin, self.screen_size[1] - margin)

            # Create candidate box object
            candidate_box = self.Box((random_x, random_y),
                                     self.box_parameters['size'])

            # Check if candidate box collides with any of the previously
            # generated boxes
            if not any(self.collision_check(candidate_box, box)
                       for box in boxes):
                # Append candidate box to list of boxes
                boxes.append(candidate_box)

                # Increment counter of generated boxes
                i += 1

        return boxes

    def collision_check(self, candidate_box, box):
        """
        Check for collision of two boxes. Collision defined by mininum distance
        between the centers of the boxes in box parameters.
        :param candidate_box: candidate box object
        :param box: box object already added to current set of boxes
        :return: Flag that indicates if the two boxes collide
        """

        # Compute euclidean distance between box centers
        dx = candidate_box.pos[0] - box.pos[0]
        dy = candidate_box.pos[1] - box.pos[1]
        distance = sqrt(dx ** 2 + dy ** 2)

        # Collision if distance below threshold
        if distance < self.box_parameters['min_dist']:
            return True
        else:
            return False

    def show(self, trial_start, start_delay, screen):
        """
        Draw corsi sequence. Boxes are highlighted for a
        specified duration (self.box_parameters['t_highlight']) if application
        in state "ShowSequence". In state "UserInput", set of boxes is
        displayed without highlighting.
        """

        # Next state
        next_state = 'ShowSequence'

        # Wait specified time before starting the trial
        # Delay only used for first sequence of trial (after reading
        # instructions)
        if (time() - trial_start) > start_delay:

            # Draw first box
            if self.highlight_box_id == 0:

                # Highlight first box
                self.boxes[self.highlight_box_id].highlight = True

                # Increment box selector
                self.highlight_box_id += 1

                # Set time of last box highlighting
                self.last_box_highlighted = time()

            else:

                # Get current time
                current_time = time()

                # Highlight next box if highlight duration exceeded
                if (current_time - self.last_box_highlighted) > \
                        self.box_parameters['t_highlight']:

                    # If full sequence hasn't been highlighted yet
                    if self.highlight_box_id < self.length:

                        # Disable highlighting for previous box
                        self.boxes[
                            self.highlight_box_id - 1].highlight = False

                        # Enable highlighting for current box
                        self.boxes[self.highlight_box_id].highlight = True

                        # Increment box selector
                        self.highlight_box_id += 1

                        # Set time of last box highlighting
                        self.last_box_highlighted = time()

                    # If full sequence has been highlighted
                    else:

                        # Disable highlighting for previous box
                        self.boxes[
                            self.highlight_box_id - 1].highlight = False

                        # Set state to user input
                        next_state = 'UserInput'

        # Draw all boxes
        for box in self.boxes:
            box.draw(screen)

        return next_state


class Application:

    # Declare colors and fonts as static class variables
    BLACK, WHITE = (0, 0, 0), (255, 255, 255)
    BACKGROUND_COLOR = WHITE
    RED, GREEN, = (255, 0, 0), (0, 255, 0)
    BLUE, YELLOW = (0, 0, 255), (255, 255, 0)
    font = pygame.font.Font(None, 80)
    font_small = pygame.font.Font(None, 40)

    def __init__(self, screen_size, box_parameters, start_delay,
                 max_participants, max_trials):
        """
        Constructor for application class. This class instantiates the GUI
        and handles all interaction with the participant.
        :param screen_size: tuple (int, int) | (width, height)
        :param box_parameters: dict | box parameters (number, size, dist., ...)
        :param start_delay: float | time before first corsi box is shown in s
        :param max_participants: int | maximum number of participants
        :param max_trials: int | maximum number of attempts per participant
        """

        # Initialize PyGame
        pygame.init()

        # Set screen size
        self.screen_size = screen_size
        pygame.display.set_mode((self.screen_size[0],
                                 self.screen_size[1]), 0, 32)

        # Set application title
        pygame.display.set_caption("Corsi Block Tapping Test")

        # Get screen handle
        self.screen = pygame.display.get_surface()

        # Declare interface for text input
        self.text_input = pygame_textinput.TextInput()

        # Set initial state of the application
        self.state = 'Participant_ID'

        # Initialize participant to None. Participant object will be created
        # when unique participant ID is provided
        self.participant = None

        # Initialize sequence object. New sequences will be created by
        # by generating a new set of boxes
        self.sequence = Sequence(screen_size, box_parameters)

        # Max number of attempts
        self.max_trials = max_trials

        # Set flag to indicate end of a trial
        self.trial_over = False

        # Set maximum number of participants
        self.max_participants = max_participants

        # Set delay time between instruction and sequence presentation
        self.start_delay = int(start_delay)

        # Set start time of first trial
        self.trial_start = 0

        # Load instruction image
        self.instruction_image = pygame.image.load("InstructionImage.png")

    def start(self):
        """
        Start the application. This function contains the main PyGame event
        loop.
        """

        # Loop until execution is terminated in GUI
        while True:
            # Create blank screen
            self.screen.fill(self.BACKGROUND_COLOR)

            # Handle events to set application state
            self.handle_events()

            # Update application based on application state and
            # automatic transitions between states
            self.update()

            # Refresh screen
            pygame.display.update()

    def handle_events(self):
        """
        Handle all available events.
        """

        # Get list of events
        events = pygame.event.get()

        # Iterate over all events
        for event in events:

            # Pressing ESC or clicking X
            if event.type == QUIT or (event.type == KEYDOWN and
                                      event.key == K_ESCAPE):
                # Write results to CSV
                if self.participant is not None:
                    self.participant.write_csv()
                pygame.quit()
                sys.exit()

            # STATE = Participant_ID
            if self.state == 'Participant_ID':
                self.handle_id_input(event)

            # STATE = Instructions
            elif self.state == 'Instructions':
                self.handle_instructions_input(event)

            # STATE = UserInput
            elif self.state == "UserInput":
                self.handle_user_input(event)

            # STATE = Feedback
            elif self.state == 'Feedback':
                self.handle_feedback_input(event)

    def handle_id_input(self, event):

        # Update text input interface
        self.text_input.update([event])

        # Check if valid participant ID provided
        if event.type == KEYDOWN and event.key == K_RETURN:
            try:
                # Cast text input to integer
                participant_id = int(self.text_input.get_text())
            except ValueError:
                # Set participant_id to None if invalid input provided
                participant_id = None

            # Check that participant_id within range of allowed number of
            # participants
            if participant_id is not None and \
                    1 <= participant_id <= self.max_participants:
                # Create participant
                self.participant = Participant(participant_id)
                # Set application state to "Instructions"
                self.state = "Instructions"
            else:
                print("Incorrect participant ID. Please type "
                      "a number between 1 and ", self.max_participants,
                      '!')

    def handle_instructions_input(self, event):

        # Go to next state upon pressing space bar and display
        # participant ID in GUI
        if event.type == KEYDOWN and event.key == K_SPACE:
            pygame.display.set_caption("Corsi Block Tapping "
                                       "Test: Participant "
                                       + str(self.participant.participant_id))

            # Set trial start time
            self.trial_start = time()

            # Prepare the new sequence
            self.generate_sequence()

    def handle_user_input(self, event):
        """
        Handles events in state UserInput.
        :param event: PyGame event object
        """

        if event.type == MOUSEBUTTONUP:

            # Check if participant clicks on box
            for box in self.sequence.boxes:
                if box.rect.collidepoint(pygame.mouse.get_pos()) and not box.clicked:

                    # Make sure all other boxes are set to "un-clicked"
                    for box_ in self.sequence.boxes:
                        box_.clicked = False

                    # Set property of clicked box
                    box.clicked = True

                    # Check correctness of clicked box
                    if box == self.sequence.boxes[self.participant.clicks]:
                        box.correct = True

                        # If number of clicks equal to sequence length, user
                        # input for entire sequence correct
                        if self.participant.clicks == self.sequence.length - 1:
                            self.sequence.correct = True
                            self.state = "Feedback"
                        # If all previous clicks correct, increment number of
                        # clicks
                        else:
                            self.participant.clicks += 1
                    # If not clicked box not correct
                    else:

                        # Set box property
                        box.correct = False

                        # Set state
                        self.state = "Feedback"

                        # Increment number of errors
                        self.participant.errors += 1

                        # Mark sequence as incorrect
                        self.sequence.correct = False

    def handle_feedback_input(self, event):
        """
        Handles events in feedback state.
        :param event: PyGame event object
        """

        # Start new trial or game by hitting space bar
        if event.type == KEYDOWN and event.key == K_SPACE:

            # If trial is over and maximum number of trials not
            # reached
            if self.trial_over and \
                    self.participant.current_trial < self.max_trials:
                # Increment attempt counter
                self.participant.current_trial += 1

                # Reset participant's corsi span to 2 for new trial
                self.participant.corsi_span = 2

                # Reset errors
                self.participant.errors = 0

                # Reset game over flag
                self.trial_over = False

            # If not at the end of last trial, generate new sequence
            if not (self.trial_over and
                    self.participant.current_trial == self.max_trials):
                # Generate new sequence
                self.generate_sequence()

    def generate_sequence(self):
        """
        Prepare a new trial. Generate new random boxes and reset all relevant
        parameters.
        """

        # Get sequence length
        sequence_length = self.participant.corsi_span + 1

        # Create new sequence
        self.sequence.generate(sequence_length)

        # Set new state
        self.state = "ShowSequence"

        # Set number of user_clicks to 0
        self.participant.clicks = 0

    def update(self):
        """
      Update visual appearance based on current state of the application. For
      transitions that don't required a user input, this might result in a
      change of the application state.
      """

        # Set new state to current state
        new_state = self.state

        if self.state == 'Participant_ID':
            self.show_id_input()

        elif self.state == 'Instructions':
            self.show_instructions()

        elif self.state in ['ShowSequence', 'UserInput']:
            new_state = self.sequence.show(self.trial_start, self.start_delay,
                                           self.screen)

        elif self.state == 'Feedback':
            self.show_feedback()

        else:
            print('Unknown state. Exit...')
            exit()

        # Set application state which might have changed due to automatic
        # transitions (see self.sequence.show())
        self.state = new_state

    def show_id_input(self):
        """
        Show input field for participant ID.
        """

        self.draw_text("Corsi Block Tapping Test", self.font, self.BLACK,
                       self.BACKGROUND_COLOR, 150)
        self.draw_text("Please enter your participant ID", self.font_small,
                       self.BLACK,
                       self.BACKGROUND_COLOR, SCREEN_SIZE[1] * .8)
        self.screen.blit(self.text_input.get_surface(),
                         (SCREEN_SIZE[0] * .5, SCREEN_SIZE[1] * .5))

    def show_instructions(self):
        """
        Show instruction image.
        """

        self.screen.blit(self.instruction_image, (0, 0))

    def show_feedback(self):
        """
        Display feedback depending on the user input to the last sequence.
        Based on the number of trials and errors, either a new sequence will
        be initiated or the experiment is over.
        :return:
        """

        # 3 scenarios based on user input to sequence
        # 1: Last sequence was correct
        if self.sequence.correct:

            # Set message to be displayed
            message = "Great job!"

            # Reset errors to 0 after correct sequence
            self.participant.errors = 0

            # Set current corsi span to length of sequence
            self.participant.corsi_span = self.sequence.length

            # If current sequence length equals number of boxes, experiment
            # is over and participant wins
            if self.sequence.length == self.sequence.box_parameters['n_boxes']:
                # Trial is over
                self.trial_over = True

                # Set message to be displayed
                message = "Congratulations! You won!"

        # 2: Last sequence was incorrect, but one remaining attempt
        elif self.participant.errors == 1:

            # Set message to be displayed
            message = "One more try!"

        # If errors = 2: game over, give feedback i.e. corsi span
        # and reset values for new game
        else:

            # Set message to be displayed
            message = "Trial finished!"

            # Game is over
            self.trial_over = True

        # Update participant statistics after each trial
        if self.trial_over:
            self.participant.update_statistics()

        # Show message on the screen
        self.draw_text(message, self.font, self.BLACK, self.BACKGROUND_COLOR,
                       150)

        # Show current corsi span if maximum number of trials not yet reached
        if self.trial_over and self.participant.current_trial < \
                self.max_trials:
            self.draw_text("Your corsi span in trial " +
                           str(self.participant.current_trial) +
                           "/" + str(self.max_trials) + " was " +
                           str(self.participant.corsi_span),
                           self.font_small, self.BLACK, self.BACKGROUND_COLOR,
                           SCREEN_SIZE[1] * .4)
            feedback = "Press space bar for next trial!"

        # Show final corsi span if maximum number of trials reached
        elif self.trial_over and self.participant.current_trial == \
                self.max_trials:
            self.draw_text("Your final corsi span after " +
                           str(self.max_trials) + ' is ' +
                           str(round(self.participant.mean_corsi_span, 2))
                           + " +- " +
                           str(round(self.participant.std_corsi_span, 2)),
                           self.font_small, self.BLACK, self.BACKGROUND_COLOR,
                           SCREEN_SIZE[1] * .4)
            feedback = "Press ESC to close application!"
        # If trial not yet finished
        else:
            feedback = "Press space bar to continue"

        # Show feedback on the screen
        self.draw_text(feedback, self.font_small, self.BLACK,
                       self.BACKGROUND_COLOR,
                       SCREEN_SIZE[1] * .8)

    def draw_text(self, text, font, color, bgcolor, ypos):
        """
        Helper function to display text on screen.
        :param text: string to be displayed
        :param font: PyGame font object
        :param color: text color | RGB tuple
        :param bgcolor: background_color | RGB tuple
        :param ypos: y position of text
        """
        text_surface = font.render(text, True, color, bgcolor)
        text_rectangle = text_surface.get_rect()
        text_rectangle.center = (SCREEN_SIZE[0] / 2.0, ypos)
        self.screen.blit(text_surface, text_rectangle)


if __name__ == '__main__':
    Application(SCREEN_SIZE, BOX_PARAMS, START_DELAY, MAX_PARTICIPANTS,
                MAX_TRIALS).start()
