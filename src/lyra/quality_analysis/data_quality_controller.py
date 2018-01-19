from shutil import copyfile

import os
import subprocess

from lyra.quality_analysis.input_checker import InputChecker, ErrorInformation
from lyra.quality_analysis.input_correction_view import InputCorrection
from lyra.quality_analysis.run_analysis import QualityAnalysisRunner


class DataQualityController:
    """Controller for the input correction application."""
    def __init__(self):
        self.analysis = None
        self.input_checker = None
        self.input_correction = None
        self.program_name = None
        self.input_filename = None
        self.path = "example/"

    def run(self):
        """Starts the input correction application."""
        self.input_correction = InputCorrection(self)
        self.input_correction.mainloop()

    def check_new_val(self, error: ErrorInformation) -> ErrorInformation:
        """Checks if a value fulfils an assumption

        :param error: the current error that should be checked
        :return: the error with an adapted error message or None if no error was found
        """
        return self.input_checker.check_assmp(error)

    def start_analysis(self, program_name, input_filename):
        """Starts the assumtion analysis.

        :param program_name: name of the python program that will be analyzed
        :param input_filename: name of the input file
        :return: errors found by the input checker
        """
        self.program_name = program_name
        self.input_filename = input_filename
        self.input_checker = InputChecker(self.path, self.input_filename, self.program_name)
        self.analysis = QualityAnalysisRunner(self.path, self.program_name, self.input_filename)
        self.analysis.run_analysis()
        return self.analysis.run_checker()

    def check_corrected_input(self, errors):
        """Writes the new values back to the input file and runs the input checker.

        :param errors: current errors with information about new values
        :return: errors found by the input checker
        """
        if len(errors) > 0:
            new_values = [(e.location, e.new_value) for e in errors]
            new_values = sorted(new_values, key=lambda val: val[0])
            self.write_new_values(new_values)
        errors = self.analysis.run_checker()
        if len(errors) == 0:
            self.execute_input_program()
        return errors

    def write_new_values(self, new_values):
        """Writes the new values to the input file.

        :param new_values: sorted List of tuples (location, new value)
        """
        curr_val_index = 0
        curr_loc = new_values[curr_val_index][0]
        with open(self.path + self.input_filename, "r") as input_file:
            with open(self.path + self.input_filename + ".temp", "w") as input_file_tmp:
                line_num = 0
                line = ""
                while curr_val_index < len(new_values) or line:
                    line = input_file.readline()
                    if line_num+1 == curr_loc:
                        input_file_tmp.write(new_values[curr_val_index][1] + "\n")
                        curr_val_index += 1
                        if curr_val_index < len(new_values):
                            curr_loc = new_values[curr_val_index][0]
                        else:
                            curr_loc = -1
                    else:
                        input_file_tmp.write(line)
                    line_num += 1
        copyfile(self.path + self.input_filename + ".temp", self.path + self.input_filename)
        os.remove(self.path + self.input_filename + ".temp")

    def execute_input_program(self):
        """Executes the analyzed program."""
        print("\n --- EXECUTING PROGRAM ---\n")
        with open(self.path + "execute_program.sh", "w") as exec_program:
            exec_program.write(f"python3.6 {self.path}{self.program_name}.py <<EOF\n")
            with open(self.path + self.input_filename, "r") as input_file:
                for line in input_file:
                    exec_program.write(line)
            exec_program.write(f"\nEOF")
        subprocess.call("./" + self.path + "execute_program.sh", shell=True)
        print("")

if __name__ == "__main__":
    DataQualityController().run()
