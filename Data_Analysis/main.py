import sys
import pandas
import matplotlib.pyplot as plt
from fpdf import FPDF
import re

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
    ip_counter = pandas.DataFrame(columns=['ip', 'occurrences', 'first_time', 'last_time'])
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
                    
                
    #Sort dataframe by occurrences
    ip_counter = ip_counter.sort_values(by=['occurrences'], ascending=False)
    return ip_counter

#Function that creates a final report in pdf format
def create_pdf(device_info, ip_counter):
    #Initial setup
    pdf = FPDF()
    pdf.add_page()
    #Add title
    pdf.set_font('Arial', 'B', 24)
    pdf.cell(0, 10, 'Analysis report', 0, 1, 'C')
    #Report
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, 'This is a report of the analysis of the data from the UniFi controller.', 0, 1, 'L')

    #Function that creates a table with the device info
    def add_device_info():
        #Add title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Device info', 0, 1, 'L')
        #Creates a talbe with the device info
        #Add headers
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(60, 10, 'Device name', 1, 0, 'L')
        pdf.cell(60, 10, 'IP address', 1, 0, 'L')
        pdf.cell(60, 10, 'MAC address', 1, 1, 'L')
        #Add data
        pdf.set_font('Arial', '', 12)
        for _, row in device_info.iterrows():
            pdf.cell(60, 10, row[0], 1, 0, 'L')
            pdf.cell(60, 10, row[1], 1, 0, 'L')
            pdf.cell(60, 10, row[2], 1, 1, 'L')

    def add_common_ip():
        ##Add Graphics
        #Add title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Most common IP addresses', 0, 1, 'L')
        #Add image
        pdf.image('local\\visualisations\\most_common_ip.png', x=10, y=pdf.get_y(), w=180)
        pdf.cell(0, 150, '', 0, 1, 'C')
        ##Add table
        pdf.set_font('Arial', 'B', 12)
        cell_width = 45
        pdf.cell(cell_width, 10, 'IP address', 1, 0, 'L')
        pdf.cell(cell_width, 10, 'Occurrences', 1, 0, 'L')
        pdf.cell(cell_width, 10, 'First time', 1, 0, 'L')
        pdf.cell(cell_width, 10, 'Last time', 1, 1, 'L')
        #Add data
        pdf.set_font('Arial', '', 12)
        for _, row in ip_counter.iterrows():
            pdf.cell(cell_width, 10, row[0], 1, 0, 'L')
            pdf.cell(cell_width, 10, str(row[1]), 1, 0, 'L')
            pdf.cell(cell_width, 10, row[2], 1, 0, 'L')
            pdf.cell(cell_width, 10, row[3], 1, 1, 'L')


      

    #Call functions
    add_device_info()
    add_common_ip()
    #Output pdf
    pdf.output('output.pdf', 'F')


def main():
    #path = sys.argv[1]
    path = 'local\\usgmessages_processed_02-04-2023_20-57-32'
    device_info = import_csv(f'{path}\\device_info.csv')
    file_type = extract_file_type(path)
    df = import_csv(f'{path}\\{file_type}.csv')

    #Visualise the most common IP addresses
    ip_counter = common_ip(df)
    num_of_ip = 10
    make_bar_chart(ip_counter.head(num_of_ip), 'ip', 'occurrences', f'Top {num_of_ip} IP Addresses', 'IP address', 'Occurrences', 'local\\visualisations\\most_common_ip.png')

    create_pdf(device_info, ip_counter)

if __name__ == '__main__':
    main()