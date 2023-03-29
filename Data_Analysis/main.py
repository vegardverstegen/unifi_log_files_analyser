import sys
import pandas
import matplotlib.pyplot as plt

#Function that imports a csv file and returns a pandas dataframe
def import_csv(path):
    data = pandas.read_csv(path, sep=',', quotechar='|')
    return data

#Function that extracts the file type from the path
def extract_file_type(path):
    file_type = path.split('/')[-1]
    file_type = file_type.split('\\')[-1]
    file_type = file_type.split('.')[0].split('_')[0]
    return file_type

#Function that makes a bar chart from a pandas dataframe with matplotlib
def make_bar_chart(dataframe, x_axis, y_axis, title, x_label, y_label, save_path):
    #List of colors to use for the bars. Good colors for presenting scientific data
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    plt.bar(dataframe[x_axis], dataframe[y_axis], color=colors)
    #Make x_axis labels smaller
    plt.xticks(rotation=30, size=8, ha='right')
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    #Adjust sizing
    plt.tight_layout()
    plt.savefig(save_path)

def common_ip(dataframe):
    #Make dataframe with IP addresses and occurrences
    ip_counter = dataframe['IP addresses'].value_counts().rename_axis('ip').reset_index(name='occurrences')
    #Strip and remove brackets from IP addresses strings
    ip_counter['ip'] = ip_counter['ip'].str.strip('[]')
    #Remove entry with no IP address
    ip_counter = ip_counter[ip_counter.ip != '']
    #Sort dataframe by occurrences
    ip_counter = ip_counter.sort_values(by=['occurrences'], ascending=False)
    return ip_counter

def extract_device_name(dataframe):
    #Loop through Message and IP addresses columns
    corrolation = {}
    for _, i in dataframe.iterrows():
        if 'argv[2]' in i['Message']:
            if i['IP addresses'].strip('[]') not in corrolation.keys():
                corrolation[i['IP addresses']] = [i['Message'].split('=')[1].strip()]
            else:
                corrolation[i['IP addresses']].append(i['Message'].split('=')[1].strip())
        
    return corrolation



def main():
    #path = sys.argv[1]
    path = 'local\\usgmessages_29-03-2023_19-50-00.csv'
    file_type = extract_file_type(path)
    df = import_csv(path)

    #Visualise the most common IP addresses
    ip_counter = common_ip(df)
    make_bar_chart(ip_counter.head(10), 'ip', 'occurrences', 'Most common IP addresses', 'IP address', 'Occurrences', 'local\\visualisations\\most_common_ip.png')

    #List of device names associated with IP addresses
    device_names = extract_device_name(df)
    print(device_names)

if __name__ == '__main__':
    main()