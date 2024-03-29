# myapp/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
import csv
from datetime import datetime
from django.views.decorators.http import require_POST

dev = False # True if running from laptop

if not dev:
    JOBS_FILE_PATH = '/home/diviwebapp/divi-webapp/divi/myapp/jobs.csv'
    JOBS_LOG_FILE_PATH = '/home/diviwebapp/divi-webapp/divi/myapp/jobs_log.csv'
    PROFILE_FILE_PATH = '/home/diviwebapp/divi-webapp/divi/myapp/profiles.csv'
    USER_DATA_FILE_PATH = '/home/diviwebapp/divi-webapp/divi/myapp/user_data_log.csv'
else:
    JOBS_FILE_PATH = 'myapp/jobs.csv'
    JOBS_LOG_FILE_PATH = 'myapp/jobs_log.csv'
    PROFILE_FILE_PATH = 'myapp/profiles.csv'
    USER_DATA_FILE_PATH = 'myapp/user_data_log.csv'


def log_user_data(request):
    client_ip = get_client_name(request)
    path = request.path_info
    time = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    update_user_data_log(client_ip, path, time)


def get_client_name(request):
    profile_name = request.session.get('selected_profile')
    return profile_name


def update_user_data_log(ip, path, time):
    log_file_path = USER_DATA_FILE_PATH

    # Create a new line for the CSV file
    new_log_entry = {
        'ip': ip,
        'path': path,
        'time': time,
    }

    # Append the new line to the CSV file
    with open(log_file_path, 'a', newline='') as csvfile:
        fieldnames = ['ip', 'path', 'time']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # If the file is empty, write the header
        if csvfile.tell() == 0:
            writer.writeheader()

        writer.writerow(new_log_entry)


@require_POST
def complete_job(request):
    log_user_data(request)
    selected_profile = request.session.get('selected_profile', None)
    selected_job_name = request.POST.get('selected_job_name', None)
    date_time_completed = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')

    if selected_job_name:
        # Update jobs.csv
        update_jobs_csv(selected_job_name)

        # Update jobs log
        update_jobs_log(selected_profile, selected_job_name, date_time_completed)

        # Update profiles.csv
        update_profiles_csv(selected_profile, selected_job_name)

        messages.success(request, f'Job "{selected_job_name}" completed successfully!')
    else:
        messages.error(request, 'Please select a valid job.')

    return redirect('jobs')


def update_jobs_log(profile_name, job, date_completed):
    log_file_path = JOBS_LOG_FILE_PATH  # Replace with the actual path to your CSV file

    # Create a new line for the CSV file
    new_log_entry = {
        'profile_name': profile_name,
        'job': job,
        'date_completed': date_completed,
    }

    # Append the new line to the CSV file
    with open(log_file_path, 'a', newline='') as csvfile:
        fieldnames = ['profile_name', 'job', 'date_completed']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # If the file is empty, write the header
        if csvfile.tell() == 0:
            writer.writeheader()

        writer.writerow(new_log_entry)


def update_jobs_csv(job_name):
    # Update jobs.csv with the current date and time
    with open(JOBS_FILE_PATH, 'r', newline='') as csvfile:
        jobs_list = list(csv.DictReader(csvfile))

    for job in jobs_list:
        if job['name'] == job_name:
            job['last_completed'] = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            break

    with open(JOBS_FILE_PATH, 'w', newline='') as csvfile:
        fieldnames = jobs_list[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(jobs_list)


def update_profiles_csv(profile_name, job_name):
    # Update profiles.csv with a new line for the completed job
    profiles_file_path = PROFILE_FILE_PATH

    # Read existing fieldnames from the CSV file
    with open(profiles_file_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        fieldnames = next(reader)

    # Update profiles.csv with a new line for the completed job
    with open(profiles_file_path, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Create a new profile line dictionary, skipping the first field
        new_profile_line = {field: 'None' if field != profile_name else job_name for field in fieldnames}

        writer.writerow(new_profile_line)


def jobs(request):
    log_user_data(request)
    selected_profile = request.session.get('selected_profile', None)
    jobs_list = load_jobs()

    if request.method == 'POST':
        selected_profile = request.POST.get('selected_profile', None)

        if selected_profile:
            request.session['selected_profile'] = selected_profile
            messages.success(request, f'Profile "{selected_profile}" selected successfully!')
            return redirect('jobs')
        else:
            messages.error(request, 'Please select a valid profile.')

    # Calculate time difference and update job color
    for job in jobs_list:
        last_completed_time = datetime.strptime(job['last_completed'], "%Y_%m_%d_%H_%M_%S")
        current_time = datetime.now()
        time_difference = current_time - last_completed_time
        cooldown_hours = int(job['cooldown'])

        if time_difference.total_seconds() / 3600 < cooldown_hours:
            job['color'] = 'red'
        else:
            job['color'] = 'normal'

    return render(request, 'myapp/jobs.html', {'selected_profile': selected_profile, 'jobs_list': jobs_list})


def job_details(request):
    log_user_data(request)
    selected_job_name = request.POST.get('selected_job_name', None)

    if request.method == 'POST':
        if request.POST.get('complete_button'):
            return complete_job(request)

    if selected_job_name:
        selected_job_details = get_job_details(selected_job_name)

        # Convert cooldown from hours to weeks, days, and hours
        selected_job_details['cooldown_formatted'] = convert_cooldown(selected_job_details['cooldown'])

        # Check if the "Complete" button should be shown
        selected_job_details['show_complete_button'] = show_complete_button(selected_job_details)

        return render(request, 'myapp/job_details.html', {'selected_job_details': selected_job_details})
    else:
        messages.error(request, 'Please select a valid job.')

    return redirect('jobs')


def convert_cooldown(cooldown):
    # Convert cooldown from hours to weeks, days, and hours
    cooldown = int(cooldown)
    weeks = cooldown // (7 * 24)
    days = (cooldown % (7 * 24)) // 24
    hours = cooldown % 24

    return f"{weeks} weeks, {days} days, {hours} hours"


def get_job_details(job_name):
    with open(JOBS_FILE_PATH, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['name'] == job_name:
                return row
    return None


def load_jobs():
    jobs_list = []
    with open(JOBS_FILE_PATH, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            jobs_list.append(row)
    return sort_by_reward(jobs_list)


def sort_by_reward(task_list):
    # Use the sorted function to sort the list based on the 'reward' key
    sorted_list = sorted(task_list, key=lambda x: int(x['reward']))

    return sorted_list


def profiles(request):
    log_user_data(request)
    with open(PROFILE_FILE_PATH, newline='') as csvfile:
        reader = csv.reader(csvfile)
        profiles = next(reader)

    return render(request, 'myapp/profiles.html', {'profiles': profiles})


def scores(request):
    log_user_data(request)
    totals_per_profile = find_totals_per_profile()
    # print(read_csv_and_transpose())
    return render(request, 'myapp/scores.html', {'totals_per_profile': totals_per_profile})


def show_complete_button(selected_job_details):
    last_completed_time = datetime.strptime(selected_job_details['last_completed'], "%Y_%m_%d_%H_%M_%S")
    current_time = datetime.now()
    time_difference = current_time - last_completed_time
    cooldown_hours = int(selected_job_details['cooldown'])

    return time_difference.total_seconds() / 3600 > cooldown_hours


def find_totals_per_profile(file_path=PROFILE_FILE_PATH, jobs_file=JOBS_FILE_PATH):
    # Read the CSV file
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        data = list(reader)

    # Transpose the data
    transposed_data = list(map(list, zip(*data)))

    # Read the jobs file to create a dictionary mapping job names to rewards
    job_rewards = {}
    with open(jobs_file, 'r') as jobs_file:
        jobs_reader = csv.reader(jobs_file)
        next(jobs_reader)  # Skip header
        for row in jobs_reader:
            name, _, reward, _, _ = row
            job_rewards[name] = int(reward)

    # Convert the items in each row (excluding the first entry) into rewards
    for row in transposed_data:
        for i in range(1, len(row)):
            job_name = row[i]
            if job_name == 'None' or job_name not in job_rewards:
                row[i] = 0
            else:
                row[i] = job_rewards[job_name]

    # Calculate the sum of each row (excluding the first entry)
    sums = [[row[0], sum(row[1:])] for row in transposed_data]

    totals_per_profile_with_balance = calculate_balance(sums)

    return totals_per_profile_with_balance


def get_score_details(file_path=PROFILE_FILE_PATH):
    # Read the CSV file
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        data = list(reader)

    # Transpose the data
    transposed_data = list(map(list, zip(*data)))

    return transposed_data


def scores_details(request, selected_profile):
    log_user_data(request)
    score_details = get_score_details()

    # Find the score details for the selected profile
    selected_score_details = [details[1:] for details in score_details if details[0] == selected_profile][0]

    # Filter out 'None' values
    selected_score_details = [detail for detail in selected_score_details if detail != 'None']

    reward_details = get_rewards_per_job_name(selected_score_details)

    return render(request, 'myapp/scores_details.html',
                  {'selected_profile': selected_profile, 'score_details': selected_score_details,
                   'reward_details': reward_details})


def calculate_balance(totals_per_profile):
    total_rewards = sum([total[1] for total in totals_per_profile])
    num_profiles = len(totals_per_profile)

    # Calculate balance for each profile using the provided equation
    for i in range(num_profiles):
        num_rewards = totals_per_profile[i][1]
        balance = ((num_profiles / (num_profiles - 1)) * num_rewards -
                   (num_profiles / (num_profiles ** 2 - num_profiles)) * total_rewards)

        # Round the balance to 2 decimal points
        rounded_balance = round(balance, 2)

        # Add the rounded balance to the existing tuple (profile, total_reward)
        totals_per_profile[i] = (totals_per_profile[i][0], totals_per_profile[i][1], rounded_balance)

    return totals_per_profile


def add_job(request):
    log_user_data(request)
    if request.method == 'POST':
        name = request.POST.get('name')

        description = repr(request.POST.get('description'))
        description = description.replace('\\r\\n', '<br>')
        description = description[1:-1]

        reward = request.POST.get('reward')
        cooldown_weeks = request.POST.get('cooldown_weeks')
        cooldown_days = request.POST.get('cooldown_days')
        cooldown_hours = request.POST.get('cooldown_hours')

        if name and description and reward and cooldown_weeks and cooldown_days and cooldown_hours:
            # Calculate cooldown in hours
            cooldown_in_hours = int(cooldown_weeks) * 7 * 24 + int(cooldown_days) * 24 + int(cooldown_hours)

            # Update jobs.csv with the new job
            with open(JOBS_FILE_PATH, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([name, description, reward, cooldown_in_hours, '0001_01_01_00_00_00'])

            return redirect('jobs')  # Redirect to jobs page after adding the job

    return render(request, 'myapp/add_job.html')  # Render the add_job.html template


def get_rewards_per_job_name(job_names, file_path=JOBS_FILE_PATH):
    # Read the CSV file
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        data = list(reader)

    # Create a dictionary to store job names and their rewards
    job_rewards = {}

    # Populate the dictionary from the CSV data
    for row in data[1:]:  # Skip the header row
        job_name = row[0]
        reward = int(row[2])  # Assuming reward is in the third column, adjust if needed
        job_rewards[job_name] = reward

    # Create a list of rewards corresponding to the input job names
    rewards_list = [job_rewards.get(job_name, 0) for job_name in job_names]

    return rewards_list
