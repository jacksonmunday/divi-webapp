import json
from django.shortcuts import render, redirect
from django.contrib import messages
import csv
from datetime import datetime
from django.views.decorators.http import require_POST

# DEVELOPMENT FIELDS ---------------------------------------------------------------------------------------------------

dev = True  # True if running from laptop

if not dev:
    JOBS_FILE_PATH = '/home/diviwebapp/divi-webapp/divi/myapp/jobs.csv'
    PROFILE_FILE_PATH = '/home/diviwebapp/divi-webapp/divi/myapp/profiles.json'
    USER_DATA_FILE_PATH = '/home/diviwebapp/divi-webapp/divi/myapp/user_data_log.csv'
    DATES_DATA_FILE_PATH = '/home/diviwebapp/divi-webapp/divi/myapp/dates.json'
    COMPLETED_JOBS_DATA_FILE_PATH = '/home/diviwebapp/divi-webapp/divi/myapp/completed_jobs.json'
else:
    JOBS_FILE_PATH = 'myapp/jobs.csv'
    PROFILE_FILE_PATH = 'myapp/profiles.json'
    USER_DATA_FILE_PATH = 'myapp/user_data_log.csv'
    DATES_DATA_FILE_PATH = 'myapp/dates.json'
    COMPLETED_JOBS_DATA_FILE_PATH = 'myapp/completed_jobs.json'


# ----------------------------------------------------------------------------------------------------------------------


class Utils:

    def __init__(self):
        pass

    @staticmethod
    def convert_str_to_bool(string):
        if string.lower() == 'false':
            result = False
        else:
            result = bool(string)
        return result

    @staticmethod
    def get_date_time():
        return datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    @staticmethod
    def format_date(input_str):
        try:
            # Parse the input string using the specified format
            dt_object = datetime.strptime(input_str, "%Y_%m_%d_%H_%M_%S")

            if dt_object.minute < 10:
                formatted_date = f'{dt_object.day} {dt_object.strftime("%B")} {dt_object.year}  at {dt_object.hour}:0{dt_object.minute}'
            else:

                formatted_date = f'{dt_object.day} {dt_object.strftime("%B")} {dt_object.year}  at {dt_object.hour}:{dt_object.minute}'

            return formatted_date
        except ValueError:
            return "Invalid date format"

    @staticmethod
    def convert_cooldown(cooldown):
        # Convert cooldown from hours to weeks, days, and hours
        cooldown = int(cooldown)
        weeks = cooldown // (7 * 24)
        days = (cooldown % (7 * 24)) // 24
        hours = cooldown % 24

        return f"{weeks} weeks, {days} days, {hours} hours"

    @staticmethod
    def show_complete_button(selected_job_details):
        last_completed_time = datetime.strptime(selected_job_details.last_completed, "%Y_%m_%d_%H_%M_%S")
        current_time = datetime.now()
        time_difference = current_time - last_completed_time
        cooldown_hours = int(selected_job_details.cooldown)

        return time_difference.total_seconds() / 3600 > cooldown_hours


class LogData:
    """
    When this class is called it will log the users data to the data log
    """

    def __init__(self, request):
        self.request = request
        self.page_view_data_path = USER_DATA_FILE_PATH

    def get_client_name(self):
        profile_name = self.request.session.get('selected_profile')
        return profile_name

    def update_user_data(self):
        # Create a new line for the CSV file
        new_log_entry = {
            'ip': self.get_client_name(),
            'path': self.request.path_info,
            'time': Utils.get_date_time(),
        }

        # Append the new line to the CSV file
        with open(self.page_view_data_path, 'a', newline='') as csvfile:
            fieldnames = ['ip', 'path', 'time']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # If the file is empty, write the header
            if csvfile.tell() == 0:
                writer.writeheader()

            writer.writerow(new_log_entry)


class Jobs:

    def __init__(self):
        self.file_path = JOBS_FILE_PATH
        self.jobs_list = self.get_job_objects()
        self.update_job_colour()
        self.update_hours_until_ready()

    def get_un_voted_jobs_from_profile(self, profile_object):
        list = []
        for job in self.jobs_list:
            for vote in profile_object.votes:
                if vote[0] == job.name:
                    list.append(job)

        return set(self.jobs_list) - set(list)

    def get_job_objects(self):
        jobs_list = []
        with open(self.file_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                job = Job(row['name'], row['description'], row['cooldown'], row['last_completed'],
                          Utils.convert_str_to_bool(row['one_off']))
                jobs_list.append(job)
        return self.sort_by_reward(jobs_list)

    def get_job_details(self, searching_job_name):
        for job in self.jobs_list:
            if job.name == searching_job_name:
                return job
        return None

    def add_new_job(self, job):
        job_exists = False

        for current_job in self.jobs_list:
            if current_job.name.lower() == job.name.lower():
                job_exists = True

        if not job_exists:
            # Update jobs.csv with the new job
            with open(JOBS_FILE_PATH, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([job.name, job.description, job.cooldown, job.last_completed, job.one_off])
        else:
            print("Job already exists")

        self.jobs_list = self.get_job_objects()

    def update_job_colour(self):
        # Calculate time difference and update job color
        for job in self.jobs_list:
            last_completed_time = datetime.strptime(job.last_completed, "%Y_%m_%d_%H_%M_%S")
            current_time = datetime.now()
            hours_since_last_completed = ((current_time - last_completed_time).total_seconds()) / 3600
            cooldown_hours = int(job.cooldown)

            if job.one_off:
                if job.last_completed == '0001_01_01_00_00_00':
                    job.colour = 'white'
                else:
                    job.colour = 'red'

            else:
                if hours_since_last_completed < cooldown_hours:
                    # Calculate the ratio between cooldown and hours_since_last_completed
                    ratio = hours_since_last_completed / cooldown_hours

                    # Map the ratio to a color between red and light orange
                    red_value = 255
                    green_value = int(ratio * 220)  # Constant for orange color
                    blue_value = int(ratio * 220)  # Constant for orange color

                    # Convert RGB values to hex
                    job.colour = "#{:02X}{:02X}{:02X}".format(red_value, green_value, blue_value)
                else:
                    job.colour = 'white'

    def update_hours_until_ready(self):
        for job in self.jobs_list:
            last_completed_time = datetime.strptime(job.last_completed, "%Y_%m_%d_%H_%M_%S")
            current_time = datetime.now()
            time_difference = current_time - last_completed_time
            remaining_hours = int(job.cooldown) - (time_difference.total_seconds() / 3600)
            if remaining_hours > 0:
                job.hours_until_ready = int(remaining_hours)
            else:
                job.hours_until_ready = 0

    def update_after_completed(self, job_name):
        """
        Updates the jobs.csv with the correct last comeplted datte
        :param job_name: name of the job string
        :return: none
        """
        for job in self.jobs_list:
            if job.name == job_name:
                job.last_completed = Utils.get_date_time()
                break
        self.update_csv_from_object_list()

    def update_csv_from_object_list(self):
        with open(self.file_path, 'w', newline='') as csvfile:
            fieldnames = ['name', 'description', 'cooldown', 'last_completed', 'one_off']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()

            for job in self.jobs_list:
                writer.writerow({
                    'name': job.name,
                    'description': job.description,
                    'cooldown': job.cooldown,
                    'last_completed': job.last_completed,
                    'one_off': job.one_off,
                })

    @staticmethod
    def sort_by_reward(jobs_list):
        # Use the sorted function to sort the list based on the 'reward' key
        sorted_list = sorted(jobs_list, key=lambda x: int(x.reward))
        return sorted_list


class Job:
    def __init__(self, name, description, cooldown, last_completed, one_off):
        self.name = name
        self.description = description
        self.cooldown = cooldown
        self.last_completed = last_completed
        self.one_off = one_off
        self.reward = 1

        self.colour = 'normal'
        self.cooldown_formatted = None
        self.time_since_last_complete = None
        self.show_complete_button = None
        self.hours_until_ready = None


class CompletedJobs:

    def __init__(self):
        self.file_path = COMPLETED_JOBS_DATA_FILE_PATH
        self.complete_jobs_list = self.load_json()

    def add_to_json(self, completed_job):
        try:
            with open(self.file_path, 'r') as file:
                existing_data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = []

        # Append new completed job data
        new_completed_job = {
            "job": {
                "name": completed_job.job.name,
                "description": completed_job.job.description,
                "reward": completed_job.job.reward,
                "cooldown": completed_job.job.cooldown,
                "last_completed": completed_job.job.last_completed,
                "one_off": completed_job.job.one_off,
                "colour": completed_job.job.colour
            },
            "participants": completed_job.participants,
            "who_pays": completed_job.who_pays,
            "formatted_date": Utils().format_date(completed_job.job.last_completed)
        }

        existing_data.append(new_completed_job)

        # Save updated JSON back to the file
        with open(self.file_path, 'w') as file:
            json.dump(existing_data, file, indent=2)

        self.complete_jobs_list = self.load_json()

    def load_json(self):
        try:
            with open(self.file_path, 'r') as file:
                completed_jobs_data = json.load(file)
                return [CompletedJob.from_json_data(job_data) for job_data in completed_jobs_data]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def get_completed_jobs_from_profile_name(self, name):
        list_ = []
        for completed_job in self.complete_jobs_list:
            for participant in completed_job.participants:
                if participant.lower() == name.lower():
                    list_.append(completed_job)
        return list_


class CompletedJob:
    """
    Object for a completed job
    """

    def __init__(self, job, participants, who_pays, formatted_date):
        self.job = job
        self.participants = participants
        self.who_pays = who_pays
        self.formatted_date = formatted_date
        self.shared_reward = self.get_shared_reward()
        self.file_path = COMPLETED_JOBS_DATA_FILE_PATH

    def print_all(self):
        print(self.job)
        print(self.participants)
        print(self.who_pays)

    def get_shared_reward(self):
        return round(int(self.job.reward) / len(self.participants), 2)

    @classmethod
    def from_json_data(cls, json_data):
        job_data = json_data.get("job", {})
        job = Job(
            job_data.get("name", ""),
            job_data.get("description", ""),
            job_data.get("cooldown", ""),
            job_data.get("last_completed", ""),
            job_data.get("one_off", ""),
        )
        participants = json_data.get("participants", [])
        who_pays = json_data.get("who_pays", [])
        formatted_date = json_data.get("formatted_date", "")
        return cls(job, participants, who_pays, formatted_date)


class Profiles:
    def __init__(self):
        self.profiles_file_path = PROFILE_FILE_PATH
        self.list_of_objects = self.load_profiles_from_json()  # Loaded everytime an object is made
        self.list_of_strings = self.get_profile_names_list()

    def create_profile(self, name):
        # Convert name to lowercase for case-insensitive comparison
        name_lower = name.lower()

        # Check if the profile already exists
        if not any(profile.name.lower() == name_lower for profile in self.list_of_objects):
            new_profile = Profile(name)
            self.save_new_profile_to_json(new_profile)
            self.load_profiles_from_json()  # reload list when new profile added
        else:
            print(f"Profile with name '{name}' already exists.")

    def save_new_profile_to_json(self, profile_object):
        try:
            with open(self.profiles_file_path, 'r') as json_file:
                existing_data = json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = []

        profile_dict = {
            "name": profile_object.name,
            "dates": profile_object.dates,
            "votes": profile_object.votes
        }

        existing_data.append(profile_dict)

        with open(self.profiles_file_path, 'w') as json_file:
            json.dump(existing_data, json_file, indent=2)

    def get_profile_names_list(self):
        new_list = []
        for profile in self.list_of_objects:
            new_list.append(profile.name)
        return new_list

    def load_profiles_from_json(self):
        profiles_list = []
        try:
            with open(self.profiles_file_path, 'r') as json_file:
                data = json.load(json_file)
                for entry in data:
                    profile = Profile(entry['name'])
                    profile.dates = entry['dates']
                    profile.votes = entry['votes']
                    profiles_list.append(profile)
        except (FileNotFoundError, json.JSONDecodeError):
            # Handle the case when the file is not found or cannot be decoded
            pass

        return profiles_list

    def get_profile_by_name(self, name):
        # Convert name to lowercase for case-insensitive comparison

        name_lower = name.lower()

        # Find the profile with the given name
        for profile in self.list_of_objects:
            if profile.name.lower() == name_lower:
                return profile

        # If the profile is not found, return None
        print(f"Profile with name '{name}' not found.")
        return None

    def update_votes(self, profile_object):
        try:
            with open(self.profiles_file_path, 'r') as json_file:
                data = json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []

        for entry in data:
            if entry['name'] == profile_object.name:
                entry['votes'] = profile_object.votes
                break

        with open(self.profiles_file_path, 'w') as json_file:
            json.dump(data, json_file, indent=2)


class Profile:
    def __init__(self, name):
        self.name = name
        self.dates = []
        self.votes = []

        self.rewards = self.get_current_rewards()
        self.loss = self.get_current_losses()
        self.balance = round(self.rewards - self.loss, 2)

    def get_current_rewards(self):
        rewards = 0
        completed_jobs = CompletedJobs().complete_jobs_list
        for completed_job in completed_jobs:
            for participant in completed_job.participants:
                if participant.lower() == self.name.lower():
                    rewards += int(completed_job.job.reward) / len(completed_job.participants)
        return round(rewards, 2)

    def get_current_losses(self):
        loss = 0
        completed_jobs = CompletedJobs().complete_jobs_list
        for completed_job in completed_jobs:
            for who_pays in completed_job.who_pays:
                if who_pays.lower() == self.name.lower():
                    loss += int(completed_job.job.reward) / len(completed_job.who_pays)
        return round(loss, 2)

    def add_reward_vote(self, job_name, vote):
        self.votes.append([job_name, vote])


@require_POST
def complete_job(request):
    LogData(request).update_user_data()
    selected_profile = request.session.get('selected_profile', None)
    selected_job_name = request.POST.get('selected_job_name', None)

    if selected_job_name:
        Jobs().update_after_completed(selected_job_name)
        job_object = Jobs().get_job_details(selected_job_name)
        completed_job_object = CompletedJob(job=job_object,
                                            participants=[selected_profile],
                                            who_pays=list(set(Profiles().list_of_strings) - set([selected_profile])),
                                            formatted_date=Utils().format_date(job_object.last_completed))

        CompletedJobs().add_to_json(completed_job_object)

        messages.success(request, f'Job "{selected_job_name}" completed successfully!')
    else:
        messages.error(request, 'Please select a valid job.')

    return redirect('jobs')


def jobs(request):  # GOOD
    LogData(request).update_user_data()
    selected_profile = request.session.get('selected_profile', None)
    jobs_list = Jobs().jobs_list

    if selected_profile:
        for profile in Profiles().list_of_objects:
            if profile.name.lower() == request.session.get('selected_profile', None).lower():
                if len(profile.votes) != len(jobs_list):
                    return redirect('voting')

    if request.method == 'POST':
        selected_profile = request.POST.get('selected_profile', None)

        if selected_profile:

            request.session['selected_profile'] = selected_profile
            messages.success(request, f'Profile "{selected_profile}" selected successfully!')
            return redirect('jobs')
        else:
            messages.error(request, 'Please select a valid profile.')

    return render(request, 'myapp/jobs.html', {'selected_profile': selected_profile, 'jobs_list': jobs_list})


def job_details(request):  # GOOD
    LogData(request).update_user_data()
    selected_job_name = request.POST.get('selected_job_name', None)

    if request.method == 'POST':
        if request.POST.get('complete_button'):
            return complete_job(request)

    if selected_job_name:
        job = Jobs().get_job_details(selected_job_name)

        # Convert cooldown from hours to weeks, days, and hours
        job.cooldown_formatted = Utils().convert_cooldown(job.cooldown)

        # Calculate and display "Time since last complete"
        last_completed_time = datetime.strptime(job.last_completed, "%Y_%m_%d_%H_%M_%S")
        current_time = datetime.now()
        time_difference = current_time - last_completed_time

        # Convert time difference to weeks, days, and hours
        weeks = time_difference.days // 7
        days = time_difference.days % 7
        hours, remainder = divmod(time_difference.seconds, 3600)

        job.time_since_last_complete = f"{weeks} weeks, {days} days, {hours} hours"

        # Check if the "Complete" button should be shown
        job.show_complete_button = Utils().show_complete_button(job)

        return render(request, 'myapp/job_details.html', {'selected_job_details': job})
    else:
        messages.error(request, 'Please select a valid job.')

    return redirect('jobs')


def profiles(request):
    LogData(request).update_user_data()
    selected_profile = request.session.get('selected_profile', None)
    profiles_ = Profiles().list_of_strings
    if selected_profile:
        profile_object = Profiles().get_profile_by_name(selected_profile)
        dates = profile_object.dates
    else:
        dates = []
    return render(request, 'myapp/profiles.html',
                  {'profiles': profiles_, 'selected_profile': selected_profile, 'dates': dates})


def scores(request):
    LogData(request).update_user_data()
    profiles_ = Profiles().list_of_objects
    return render(request, 'myapp/scores.html', {'profiles': profiles_})


def voting(request):
    selected_profile = request.session.get('selected_profile', None)
    profile_object = Profiles().get_profile_by_name(selected_profile)
    jobs_list = Jobs().get_un_voted_jobs_from_profile(profile_object)

    return render(request, 'myapp/voting.html', {'selected_profile': selected_profile, 'jobs_list': jobs_list})


def submit_prices(request):
    selected_profile = request.session.get('selected_profile', None)
    if request.method == 'POST':
        profile = Profiles().get_profile_by_name(selected_profile)
        for job_name, price in request.POST.items():
            if job_name != 'csrfmiddlewaretoken':
                profile.add_reward_vote(job_name, price)
        Profiles().update_votes(profile)

    return redirect('jobs')  # Assuming 'jobs' is the name of the desired page


def scores_details(request, selected_profile):
    LogData(request).update_user_data()
    completed_jobs = CompletedJobs().get_completed_jobs_from_profile_name(selected_profile)

    return render(request, 'myapp/scores_details.html',
                  {'selected_profile': selected_profile, 'completed_jobs': completed_jobs})


def add_job(request):
    LogData(request).update_user_data()

    if request.method == 'POST':
        name = request.POST.get('name')

        description = repr(request.POST.get('description'))
        description = description.replace('\\r\\n', '<br>')
        description = description[1:-1]

        cooldown_weeks = request.POST.get('cooldown_weeks')
        cooldown_days = request.POST.get('cooldown_days')
        cooldown_hours = request.POST.get('cooldown_hours')

        one_off = request.POST.get('one_off', False)

        if name and description and cooldown_weeks and cooldown_days and cooldown_hours:
            # Calculate cooldown in hours
            cooldown_in_hours = int(cooldown_weeks) * 7 * 24 + int(cooldown_days) * 24 + int(cooldown_hours)

            # Create the Job instance with the one_off parameter
            new_job = Job(name, description, cooldown_in_hours, '0001_01_01_00_00_00', one_off)

            # Add the new job
            Jobs().add_new_job(new_job)

            return redirect('jobs')  # Redirect to jobs page after adding the job

    return render(request, 'myapp/add_job.html')  # Render the add_job.html template


def add_profile(request):
    if request.method == 'POST':
        profile_name = request.POST.get('profile_name')

        if profile_name:
            Profiles().create_profile(request.POST.get('profile_name'))

            messages.success(request, f'Profile "{profile_name}" added successfully!')
            return redirect('profiles')  # Redirect to profiles page after adding the profile
        else:
            messages.error(request, 'Invalid form submission. Please try again.')

    return render(request, 'myapp/add_profile.html')
