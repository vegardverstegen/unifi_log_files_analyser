import sys
import csv
from datetime import datetime
import re
import os

#Class that represents a log entry
class entry:
    def __init__(self, line):
        self.line = line
        self.timestamp = self.extract_timestamp()
        self.source = self.extract_source()
        self.message = self.extract_message()

    #Transforms date into DD-MM HH:MM:SS
    def extract_timestamp(self):
        datenum = {'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'}
        slice_index = 15
        old = self.line[:slice_index]
        self.line = self.line[slice_index:]
        month = datenum[old[:3]]
        date = old[4:6]
        time = old[7:]
        string = f'{date}-{month} {time}'
        return string
    
    #Extract source of log entry
    def extract_source(self):
        source, self.line = self.line.split(':', 1)
        return source.strip()
    
    #Extract message of log entry
    def extract_message(self):
        try: 
            message, self.line = self.line.split('  ', 1)
            self.extra = self.line.strip()
        except ValueError: 
            message = self.line
            self.extra = None
        return message.strip()

#Class that represents a counted log entry 
class sorted_event:
    def __init__(self, time, source, message, extra):
        self.timestamps = [time]
        self.source = source
        self.message = message
        self.extra = extra
        self.occurrences = 1
        self.ip = self.extract_ip(message)

    def add_time(self, newtime):
        self.timestamps.append(newtime)
        self.occurrences = len(self.timestamps)

    def extract_ip(self, message):
        ip = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', message)
        return ip
    
def count_data(data):
    counted = []
    for i in data:
        time = i.timestamp
        source = i.source
        message = i.message
        extra = i.extra
        if counted:
            for j in counted:
                if source == j.source and message == j.message and extra == j.extra:
                    j.add_time(time)
                    break
            else: counted.append(sorted_event(time, source, message, extra))
        else: counted.append(sorted_event(time, source, message, extra))
    return counted

#Function that sends each line to the class
def send_to_class(file):
    data = []
    for line in file:
        data.append(entry(line))
    return data

#Function that opens the file and returns the data
def open_file(filename):
    with open(filename) as file:
        data = file.readlines()
    return data

#Function that checks if file type input is valid
def detect_log_type(arguement):
    valid_types = ['usgmessages', 'uswmessages']
    if arguement.lower() in valid_types:
        return arguement.lower()
    else:
        raise InvalidLogFileType(f"Log file type has to match on of the following: {', '.join(valid_types)}")
    
#Function that returns a short string with the date and time
def get_date_time():
    now = datetime.now()
    date_time = now.strftime("%d-%m-%Y_%H-%M-%S")
    return date_time

def extract_execute_statement(data):
    #Loop through Message and IP addresses columns
    corrolation = {'device_name': [], 'ip': [], 'mac': []}
    for index, row in enumerate(data):
        #Check for beginning of execute statement
        if 'argv[0]' in row.message:
            #Check for device name
            row = data[index+2]
            if 'argv[2]' in row.message:
                device_name = row.message.split('=')[1].strip()
                #Check for IP address
                row = data[index+3]
                if 'argv[3]' in row.message:
                    ip = row.message.split('=')[1].strip()
                    #Check for MAC address
                    row = data[index+4]
                    if 'argv[4]' in row.message:
                        mac = row.message.split('=')[1].strip()
                        #Does not add information if MAC address exists
                        if mac in corrolation['mac']: continue
                    else: mac = ''
                    #Add all values to dictionary
                    corrolation['device_name'].append(device_name)
                    corrolation['ip'].append(ip)
                    corrolation['mac'].append(mac)
    return corrolation

def create_output_folder(filetype):
    date_time = get_date_time()
    output_folder = f'{filetype}_processed_{date_time}'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    print(output_folder)
    return output_folder

#Function that takes a dictionary and writes it to a csv file
def dict_to_csv(data, destination):
    with open(f'{destination}/device_info.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Device Name', 'IP Address', 'MAC Address'])
        for i, x in enumerate(data['device_name']):
            writer.writerow([x, data['ip'][i], data['mac'][i]])
    
#Function that takes a list of objects and writes them to a csv file
def write_to_csv(data, filetype, destination):
    with open(f'{destination}/{filetype}.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Timestamp', 'Source', 'Message', 'Extra', 'Occurrences', 'IP Address'])
        for i in data:
            writer.writerow([i.timestamps, i.source, i.message, i.extra, i.occurrences, i.ip])
    

#Custom exception 
class InvalidLogFileType(Exception):
    pass

#Main function
def main():
    global file_type
    #file_type = detect_log_type(sys.argv[1])
    #filename = sys.argv[2]
    file_type = 'usgmessages'
    filename = 'local/messages'
    file = open_file(filename)

    #Set output destination
    folder = create_output_folder(file_type)

    raw_data = send_to_class(file)
    #Save device info to csv file
    device_info = extract_execute_statement(raw_data)
    dict_to_csv(device_info, folder)

    data = count_data(raw_data)
    write_to_csv(data, file_type, folder)
    
if __name__ == '__main__':
    main()