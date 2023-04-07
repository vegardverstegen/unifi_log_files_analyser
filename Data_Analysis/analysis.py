import sys
import pandas
import matplotlib.pyplot as plt
from fpdf import FPDF
import re
from datetime import datetime

#Function that imports a csv file and returns a pandas dataframe
def import_csv(path):
    data = pandas.read_csv(path, sep=',', quotechar='|')
    return data

#Function that extracts the file type from the path
def extract_file_type(path):
    file_type = path.split('/')[-1]
    file_type = file_type.split('\\')[-1]
    file_type = file_type.split('_')[0]
    return file_type

def string_to_list(string):
    lst = string.strip('[]').replace('\'', '').split(', ')
    return lst

def check_if_known_device(df, ip:str='', mac:str='', name:str='') -> bool:
    if ip in df['IP Address'].values: return True
    if mac in df['MAC Address'].values: return True
    if name in df['Device Name'].values: return True
    return False

def get_known_device(df, ip:str='', mac:str='', name:str='') -> dict:
    if ip in df['IP Address'].values:
        row = df.loc[df['IP Address'] == ip]
    if mac in df['MAC Address'].values:
        row = df.loc[df['MAC Address'] == mac]
    if name in df['Device Name'].values:
        row = df.loc[df['Device Name'] == name]
    return {'name': row['Device Name'].values[0], 'ip': row['IP Address'].values[0], 'mac': row['MAC Address'].values[0]}

def get_known_device_list(known_df, df):
    known_device_list = []
    for _, row in df.iterrows():
        if check_if_known_device(known_df, ip=row['ip']):
            known_device_list.append(get_known_device(known_df, ip=row['ip']))
    return known_device_list

#Takes two datetimes in the format 'dd-mm HH:MM:SS' and returns the times in the order 'earliest time', 'latest time'
def compare_times(time1: str, time2: str) -> tuple:
    d1, m1, H1, M1, S1 = re.split(' |:|-', time1)
    d2, m2, H2, M2, S2 = re.split(' |:|-', time2)
    #Add buffer for new year
    if m1 >= '10' and m2 <= '03': return time1, time2
    if m1 <= '03' and m2 >= '10': return time2, time1
    #Compare times
    if d1 < d2: return time1, time2
    elif d1 > d2: return time2, time1
    if m1 < m2: return time1, time2
    elif m1 > m2: return time2, time1
    if H1 < H2: return time1, time2
    elif H1 > H2: return time2, time1
    if M1 < M2: return time1, time2
    elif M1 > M2: return time2, time1
    if S1 < S2: return time1, time2
    elif S1 > S2: return time2, time1
    #Times are equal
    return time1, time2

def find_time_span(lst: list) -> tuple:
    earliest = lst[0]
    latest = lst[0]
    for time in lst:
        earliest, tmp = compare_times(earliest, time)
        tmp, latest = compare_times(time, latest)

    return earliest, latest

#Function that makes a bar chart from a pandas dataframe with matplotlib
def make_bar_chart(dataframe, x_axis, y_axis, title, x_label, y_label, save_path):
    plt.cla()
    #List of colors to use for the bars. Good colors for presenting scientific data
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    plt.bar(dataframe[x_axis], dataframe[y_axis], color=colors, width=0.8, linewidth=0.5)
    #Make x_axis labels smaller
    plt.xticks(rotation=30, size=8, ha='right')
    #Adding title and labels
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    #Adjust sizing
    plt.tight_layout()
    plt.savefig(save_path)

def common_ip(dataframe):
    ip_counter = pandas.DataFrame(columns=['ip', 'occurrences', 'first_time', 'last_time', 'time_delta', 'requests_per_hour'])
    #Loop through IP addresses occurences, and times in the dataframe
    for _, row in dataframe.iterrows():
        IPs = string_to_list(row['IP Address'])
        occurrences = row['Occurrences']
        times = string_to_list(row['Timestamp'])
        first_time, last_time = find_time_span(times)
        #Loop through IP addresses on each row
        for i in IPs:
            #Chek if IP exists
            if i:
                #Check if IP address is already in the dataframe row
                if i in ip_counter['ip'].values:
                    #If it is, add the occurrences, first_time and last_time to the existing row
                    ip_counter.loc[ip_counter['ip'] == i, 'occurrences'] += occurrences
                    #Extract and compare times, and update the dataframe
                    time = str(ip_counter.loc[ip_counter['ip'] == i, 'first_time'].values).strip('[]').replace('\'', '')
                    ip_counter.loc[ip_counter['ip'] == i, 'first_time'] = compare_times(first_time, time)[0]
                    time = str(ip_counter.loc[ip_counter['ip'] == i, 'last_time'].values).strip('[]').replace('\'', '')
                    ip_counter.loc[ip_counter['ip'] == i, 'last_time'] = compare_times(last_time, time)[1]
                    
                else:
                    #If it isn't, add a new row
                    ip_counter = pandas.concat([ip_counter, pandas.DataFrame([[i, occurrences, first_time, last_time]], columns=['ip', 'occurrences', 'first_time', 'last_time'])], ignore_index=True)
                    
                
    #Add a column with an average of requests per hour
    for index, row in ip_counter.iterrows():
        timedelta = (datetime.strptime(row['last_time'], '%d-%m %H:%M:%S')) - (datetime.strptime(row['first_time'], '%d-%m %H:%M:%S'))
        timedelta = timedelta.total_seconds() / 3600
        row['time_delta'] = timedelta
        if timedelta:
            row['requests_per_hour'] = int(row['occurrences'] / timedelta)

    return ip_counter

#Function that creates a final report in pdf format
def create_pdf(df, device_info, ip_counter, known_total, known_perHour):
    #Initial setup
    pdf = FPDF()
    pdf.add_page()
    #Add title
    pdf.set_font('Arial', 'B', 24)
    pdf.cell(0, 10, 'Analysis report', 0, 1, 'C')
    #Report
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, 'This is a report of the analysis of the data from the UniFi controller.', 0, 1, 'L')


    def add_known_ip(data:list):
        if data:
            #Add title
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'Known IP addresses', 0, 1, 'L')
            #Add data
            for row in data:
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, f'{row["ip"]}', 0, 1, 'L')
                pdf.set_font('Arial', '', 12)
                pdf.cell(0, 10, f'Name: {row["name"]}', 0, 1, 'L')
                pdf.cell(0, 10, f'MAC: {row["mac"]}', 0, 1, 'L')
                pdf.cell (0, 10, '', 0, 1, 'L')


    #Function that creates a table with the device info
    def add_device_info():
        cell_width = 60
        font_size = 12
        temp_font_size = font_size
        #Add title
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 10, 'Device info', 0, 1, 'L')
        #Creates a table with the device info
        #Add headers
        pdf.set_font('Arial', 'B', font_size)
        pdf.cell(cell_width, 10, 'Device name', 1, 0, 'L')
        pdf.cell(cell_width, 10, 'IP address', 1, 0, 'L')
        pdf.cell(cell_width, 10, 'MAC address', 1, 1, 'L')
        #Add data
        pdf.set_font('Arial', '', font_size)
        for _, row in device_info.iterrows():

            #Check if device name fits in the cell
            while(pdf.get_string_width(row[0]) > cell_width):   #Loop until the string fits in the cell
                temp_font_size -= 0.1                           #Reduce font size    
                pdf.set_font_size(temp_font_size)               #Set font size
            #Extra margin
            pdf.set_font_size(temp_font_size-0.3)

            #Add cell
            pdf.cell(cell_width, 10, row[0], 1, 0, 'L')

            #Reset font size
            temp_font_size = font_size
            pdf.set_font_size(font_size)

            #Add rest of cells
            pdf.cell(cell_width, 10, row[1], 1, 0, 'L')
            pdf.cell(cell_width, 10, row[2], 1, 1, 'L')

    def add_common_messages(df):
        commmon = df.sort_values(by=['Occurrences'], ascending=False).head(10)
        #Add title
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 10, 'Most common messages', 0, 1, 'L')
        #Add data
        for _, row in commmon.iterrows():
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, f'{row[1]}: {row[2]}', 0, 1, 'L')
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 10, f'Occurrences: {row[4]}', 0, 1, 'L')
            first, last = find_time_span(string_to_list(row[0]))
            pdf.cell(0, 10, f'First time: {first}', 0, 1, 'L')
            pdf.cell(0, 10, f'Last time: {last}', 0, 1, 'L')
            pdf.cell(0, 10, '', 0, 1, 'L')
        pdf.add_page()

    def add_common_ip():
        pdf.set_font('Arial', 'B', 18)
        pdf.cell(0, 10, 'Most common IP addresses', 0, 1, 'L')
    
        ##Add Graphics
        #Total
        #Add image
        pdf.image('local\\visualisations\\most_common_ip.png', x=10, y=pdf.get_y(), w=180)
        pdf.cell(0, 135, '', 0, 1, 'C')
        add_known_ip(known_total)
        pdf.add_page()

        #Per Hour
        #Add image
        pdf.image('local\\visualisations\\most_common_ip_perHour.png', x=10, y=pdf.get_y(), w=180)
        pdf.cell(0, 135, '', 0, 1, 'C')
        add_known_ip(known_perHour)
        pdf.add_page()

        ##Add table
        #Title
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'All IP addresses (table)', 0, 1, 'L')
        pdf.set_font('Arial', 'B', 10)
        cell_width = 32
        #Add headers
        pdf.cell(cell_width, 10, 'IP address', 1, 0, 'L')
        pdf.cell(cell_width, 10, 'Occurrences', 1, 0, 'L')
        pdf.cell(cell_width, 10, 'First time', 1, 0, 'L')
        pdf.cell(cell_width, 10, 'Last time', 1, 0, 'L')
        pdf.set_font_size(9)
        pdf.cell(cell_width, 10, 'Time delta (Hours)', 1, 0, 'L')
        pdf.cell(cell_width, 10, 'Requests/hour avg.', 1, 1, 'L')
        #Add data
        pdf.set_font('Arial', '', 11)
        for _, row in ip_counter.iterrows():
            pdf.cell(cell_width, 10, row[0], 1, 0, 'L')
            pdf.cell(cell_width, 10, str(row[1]), 1, 0, 'L')
            pdf.cell(cell_width, 10, row[2], 1, 0, 'L')
            pdf.cell(cell_width, 10, row[3], 1, 0, 'L')
            pdf.cell(cell_width, 10, str(round(row[4], 2)), 1, 0, 'L')
            pdf.cell(cell_width, 10, str(row[5]), 1, 1, 'L')
        

    #Call functions
    add_device_info()
    add_common_messages(df)
    add_common_ip()
    #Output pdf
    pdf.output('output.pdf', 'F')


def main():
    print('Starting analysis')
    #Get variables
    #path = sys.argv[1]
    path = 'local\\usgmessages_processed_02-04-2023_20-57-32'

    #import data
    device_info = import_csv(f'{path}\\device_info.csv')
    file_type = extract_file_type(path)
    df = import_csv(f'{path}\\{file_type}.csv')

    ##Generate visualisations
    IPs_in_chart = 10
    ip_counter = common_ip(df)
    #Visualise the most common IP addresses by total requests
    ip_counter_total = ip_counter.sort_values(by=['occurrences'], ascending=False)
    make_bar_chart(ip_counter_total.head(IPs_in_chart), 'ip', 'occurrences', f'Top {IPs_in_chart} - Total Requests', 'IP address', 'Occurrences', 'local\\visualisations\\most_common_ip.png')
    #Visualise the most common IP addresses by requests per hour
    ip_counter_perHour = ip_counter.sort_values(by=['requests_per_hour'], ascending=False)
    make_bar_chart(ip_counter_perHour.head(IPs_in_chart), 'ip', 'requests_per_hour', f'Top {IPs_in_chart} - Requests per hour', 'IP address', 'Requests per hour', 'local\\visualisations\\most_common_ip_perHour.png')

    #Make list of known devices in chart
    known_total = get_known_device_list(device_info, ip_counter_total.head(IPs_in_chart)) #Get known devices in chart for total requests
    known_perHour = get_known_device_list(device_info, ip_counter_perHour.head(IPs_in_chart)) #Get known devices in chart for requests per hour

    print('Creating report')
    create_pdf(df, device_info, ip_counter, known_total, known_perHour)

    print('Done!')

if __name__ == '__main__':
    main()