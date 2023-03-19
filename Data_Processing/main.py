import sys

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
    
    def extract_message(self):
        try: 
            message, self.line = self.line.split('  ', 1)
            self.extra = self.line.strip()
        except ValueError: 
            message = self.line
            self.extra = None
        return message.strip()
    
class sorted_event:
    def __init__(self, time, source, message, extra):
        self.timestamps = [time]
        self.source = source
        self.message = message
        self.extra = extra
        self.occurrences = 1

    def add_time(self, newtime):
        self.timestamps.append(newtime)
        self.occurrences = len(self.timestamps)
    
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

    

def send_to_class(file):
    data = []
    for line in file:
        data.append(entry(line))
    return data

def open_file(filename):
    with open(filename) as file:
        data = file.readlines()
    return data

#Added only for testing
def write_object_to_file(data):
    with open('local/output', 'a') as file:
        for i in sorted(data, key=lambda x: x.occurrences, reverse=True):
            file.write(str(i.occurrences) + '\n')
            file.write(i.source + ' ' + i.message + (' ' + i.extra if i.extra else '') + '\n\n')

def detect_log_type(arguement):
    valid_types = ['usgmessages', 'uswmessages']
    if arguement.lower() in valid_types:
        return arguement.lower()
    else:
        raise InvalidLogFileType(f"Log file type has to match on of the following: {', '.join(valid_types)}")

#Custom exception 
class InvalidLogFileType(Exception):
    pass

def main():
    global file_type
    file_type = detect_log_type(sys.argv[1])
    filename = sys.argv[2]
    #filename = 'local/messages'
    file = open_file(filename)
    raw_data = send_to_class(file)
    data = count_data(raw_data)
    write_object_to_file(data)
    

if __name__ == '__main__':
    main()