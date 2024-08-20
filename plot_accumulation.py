# Written By Jared Rennie 

# Import packages
import json,requests,sys
import pandas as pd
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# Read in Arguments 
if len(sys.argv) < 4:
    sys.exit("USAGE: <ID> <ELEMENT> <YEAR>\n Example: python plot_accumulation.py AVL prcp 2023")  
stationID = sys.argv[1]
inElem= sys.argv[2]
plotYear= int(sys.argv[3])

# Set some parameters, based upon the element being used.
if inElem =='prcp':
    elementName='Precipitation'; acisName='pcpn'; acisPrec=2; acisDur='ytd'; acisSzn=[1,1]
    acisRed='sum'; colorMap='GnBu'; normalHex='#e6b800'; unit='"'; yBuff=10; outFmt="%.2f"
if inElem =='snow':
    elementName='Snowfall'; acisName='snow'; acisPrec=1; acisDur='std'; acisSzn=[10,1]
    acisRed='sum'; colorMap='Blues'; normalHex='#2070b4'; unit='"'; yBuff=10; outFmt="%.1f"
if inElem =='gdd':
    elementName='Growing Degree Days'; acisName='gdd'; acisPrec=0; acisDur='ytd'; acisSzn=[1,1]
    acisRed='sum'; colorMap='Greens'; normalHex='#228a44'; unit=' dd'; yBuff=500; outFmt="%i"
if inElem =='cdd':
    elementName='Cooling Degree Days'; acisName='cdd'; acisPrec=0; acisDur='ytd'; acisSzn=[1,1]
    acisRed='sum'; colorMap='OrRd'; normalHex='#d62f1e'; unit=' dd'; yBuff=500; outFmt="%i"
if inElem =='hdd':
    elementName='Heating Degree Days'; acisName='hdd'; acisPrec=0; acisDur='std'; acisSzn=[10,1]
    acisRed='sum'; colorMap='PuBu'; normalHex='#0570b0'; unit=' dd'; yBuff=500; outFmt="%i"
if inElem[0:4] == 'tmax':
    elementName='Days Max Temperature >= '+inElem[4:7].strip()+'°F'; acisName='maxt'; acisPrec=0; acisDur='ytd'; acisSzn=[1,1]
    acisRed='cnt_ge_%03i' % (int(inElem[4:7].strip())); colorMap='YlOrRd'; normalHex='#e6b800'; unit=' Days'; yBuff=10; outFmt="%i"
if inElem[0:4] == 'tmin':
    elementName='Days Min Temperature >= '+inElem[4:7].strip()+'°F'; acisName='mint'; acisPrec=0; acisDur='ytd'; acisSzn=[1,1]
    acisRed='cnt_ge_%03i' % (int(inElem[4:7].strip())); colorMap='YlOrRd'; normalHex='#e6b800'; unit=' Days'; yBuff=10; outFmt="%i"

# Other Arguments that can be changed
author='Jared Rennie (@jjrennie)'
dpi=150; normals_start=1991; normals_end=2020

# Build JSON to access ACIS API (from https://www.rcc-acis.org/docs_webservices.html)
acis_url = 'http://data.rcc-acis.org/StnData'
payload = {
"output": "json",
"params": {"elems":[
               {"name":acisName,"interval":"dly","duration":acisDur,"season_start":acisSzn,"reduce":acisRed,"prec":acisPrec},
               {"name":acisName,"interval":"dly","duration":acisDur,"season_start":acisSzn,"reduce":acisRed,"normal":"1","prec":acisPrec}
               ],
           "sid":stationID,"sdate":"por","edate":"por"
          } 
}

# Make Request
try:
    r = requests.post(acis_url, json=payload,timeout=3)
    acisData = r.json()
except Exception as e:
    sys.exit('\nSomething Went Wrong With Accessing API after 3 seconds, Try Again')

# Get Station Info
stationName=acisData['meta']['name'].title()
stationState=acisData['meta']['state']
print("\nSuccessfully Got Data for: ",stationName,'\n')

# Convert Data to Pandas, get start and end year
acisPandas = pd.DataFrame(acisData['data'], columns=['Date',inElem+'_accum','normal_accum'])
stationStart=acisPandas.iloc[[0]]['Date'].values[0][0:4]
stationEnd=acisPandas.iloc[[-1]]['Date'].values[0][0:4]

# Remove Missing Data, and if Trace, convert to something else
acisPandas = acisPandas[acisPandas[inElem+'_accum'] != 'M']
acisPandas = acisPandas[acisPandas['normal_accum'] != 'M']
if inElem =='prcp' or inElem =='snow':
    acisPandas.loc[acisPandas[inElem+'_accum'] == 'T', inElem+'_accum'] = '0.00'

# Make Sure Date is datetime and data is numeric (float)
acisPandas['Date'] = pd.to_datetime(acisPandas['Date'])
acisPandas['Year'] = acisPandas['Date'].dt.year
acisPandas[inElem+'_accum'] = pd.to_numeric(acisPandas[inElem+'_accum'])
acisPandas['normal_accum'] = pd.to_numeric(acisPandas['normal_accum'])

# Need to create a Season Column that is from Jan 1st to Dec 31st.
# If input is snowfall or hdd, it needs to be Oct 1st to Sep 30th.
if inElem =='snow' or inElem =='hdd':
    acisPandas['Season'] = acisPandas.apply(lambda row: f"{row['Year']-1}-{row['Year']}" if row['Date'].month <= 9 else f"{row['Year']}-{row['Year']+1}", axis=1)
else:
    acisPandas['Season'] = acisPandas['Year']
acisPandas['DayOfSeason']=acisPandas.groupby('Season').cumcount() + 1

# Remove Seasons that aren't complete, but keep last season (usually current season). 
dayThresh=350
days_per_year = acisPandas.groupby('Season')['Date'].nunique()
complete_years = days_per_year[(days_per_year >= dayThresh) | (days_per_year.index == acisPandas['Season'].max())].index
acisPandas=acisPandas[acisPandas['Season'].isin(complete_years)]
lastDate=acisPandas.iloc[-1]['Date']

# Find the accumulation value at the end of each season, sort, and get Max/Min
eoyVals=acisPandas.groupby('Season').apply(lambda group: group.loc[group['Date'].idxmax()])
eoyVals=eoyVals[eoyVals['DayOfSeason'] >= dayThresh]
sorted_years = eoyVals.sort_values(by=inElem+'_accum')['Season']
minYear=sorted_years.iloc[0]
minVal=outFmt % (eoyVals[eoyVals['Season']==minYear][inElem+'_accum'].values[0])
maxYear=sorted_years.iloc[-1]
maxVal=outFmt % (eoyVals[eoyVals['Season']==maxYear][inElem+'_accum'].values[0])

#################################################
# PLOT
print("PLOTTING")

# Set up the plot
fig, ax1 = plt.subplots(figsize=(15, 8), edgecolor='white', facecolor='white', dpi=dpi)
plt.style.use("dark_background")

# Add grid lines
plt.grid(color='white', linestyle='--', linewidth=0.5, alpha=0.3)
ax1.set_facecolor('#808080')

# Need to account for years in season, as well as normal year
if inElem =='snow' or inElem =='hdd':
    plotYear=str(int(plotYear))+'-'+str(int(plotYear+1))
    normalYear='2020-2021'
else:
	normalYear='2020'

# Sort Again Before Plotting. User can choose to sort by end of season value, or by year. Default is by value
eoyVals=acisPandas.groupby('Season').apply(lambda group: group.loc[group['Date'].idxmax()])
#sorted_years = eoyVals.sort_values(by='Year')['Season']
sorted_years = eoyVals.sort_values(by=inElem+'_accum')['Season']

# Plot Data For Each Year
for year, group in acisPandas.groupby('Season'):
    color = sns.color_palette(colorMap, n_colors=len(sorted_years))[sorted_years.tolist().index(year)]
    plt.plot(group['DayOfSeason'], group[inElem+'_accum'],linewidth=0.5, color=color)
    
    # Plot for Max/Min Year
    if str(year) == str(maxYear):
        plt.plot(group['DayOfSeason'], group[inElem+'_accum'],linewidth=3, color=color, label='Max ('+str(maxYear)+': '+str(maxVal)+str(unit)+')') 
    if str(year) == str(minYear):
        plt.plot(group['DayOfSeason'], group[inElem+'_accum'],linewidth=3, color=color, label='Min ('+str(minYear)+': '+str(minVal)+str(unit)+')') 

    # Plot Normal
    if str(year) == str(normalYear):
        plt.plot(group['DayOfSeason'], group['normal_accum'],linewidth=3, color=normalHex, label='Avg ('+str(normals_start)+'-'+str(normals_end)+': '+str(group['normal_accum'].iloc[-1])+str(unit)+')')

    # Plot Year Used as Input
    if str(year) == str(plotYear):
        plt.plot(group['DayOfSeason'], group[inElem+'_accum'], color='black', markeredgecolor='white', linewidth=3, label=str(plotYear)+': '+str(group[inElem+'_accum'].iloc[-1])+str(unit)+'')
        plt.plot(group['DayOfSeason'].iloc[-1],group[inElem+'_accum'].iloc[-1], marker='o', color='black', markersize=10)

# Plot Legend
plt.legend(bbox_to_anchor=(0., -.102, 1., -1.02), loc=3, ncol=4, mode="expand", borderaxespad=0., fontsize=11, facecolor='#808080')

# Set X/Y limits
plt.xlim(-5, 366) 
ymin=int(acisPandas[inElem+'_accum'].min())
ymax=int(acisPandas[inElem+'_accum'].max())
ymax=int(round(float(ymax + yBuff)))
plt.ylim(ymin,ymax)

# Plot X-Axis Labels/Ticks
if inElem =='snow' or inElem =='hdd':
	month_pos=[1,32,62,93,124,152,183,213,244,274,305,336]
	month_names=["Oct 1","Nov 1","Dec 1","Jan 1","Feb 1","Mar 1","Apr 1","May 1","Jun 1","Jul 1","Aug 1","Sep 1"]
else:
	month_pos=[1,32,60,91,121,152,182,213,244,274,305,335]
	month_names=["Jan 1","Feb 1","Mar 1","Apr 1","May 1","Jun 1","Jul 1","Aug 1","Sep 1","Oct 1","Nov 1","Dec 1"]
plt.xticks(month_pos, month_names, fontsize=10, color='white')

# Plot Y-Axis Labels/Ticks (Left Side)
plt.yticks(range(ymin, ymax, yBuff), [r'{}'.format(x) for x in range(ymin, ymax, yBuff)], fontsize=10, color='white')
plt.ylabel('Accumulation ('+str(unit.strip())+')', fontsize=12, color='white')

# Plot Y-Axis Labels/Ticks (Right Side)
ax2 = ax1.twinx()
y1, y2 = ax1.get_ylim()
ax2.set_ylim(int(y1), int(y2))
ax2.figure.canvas.draw()
ax1.callbacks.connect("ylim_changed", ax2)
ax2.set_ylabel('Accumulation ('+str(unit.strip())+')', fontsize=12, rotation=270, labelpad=20)

# Plot Title/Subtitle/Annotations
plt.suptitle(str(plotYear)+' Accumulated '+elementName+' For '+stationName+', '+stationState, fontsize=17,color='white')
plt.title('Station ID: '+stationID+' | Period of Record: '+str(stationStart)+'-'+str(stationEnd), fontsize=13,color='white')
plt.annotate('Source: ACIS | Generated by '+author+' | Data up to '+lastDate.strftime('%Y-%m-%d'),xy=(0.355, 0.965), xycoords='axes fraction', fontsize=7,horizontalalignment='right', verticalalignment='bottom')

# Save and Close
plt.savefig('./'+stationID+'_accum_'+inElem+'_'+str(plotYear)+'.png', dpi=dpi,bbox_inches='tight')
plt.clf()
plt.close()

# Done! Close Program
print('DONE!')
sys.exit()