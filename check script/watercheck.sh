#!/bin/sh
#Designed for Openwrt. Cron this every hour. Requires jq

my_smartphone_mac="01:23:45:67:89:ab"
aigues_user="user"
aigues_password="passwd"

aigueselxpy_folder="/opt/usr/sbin"
bins_folder="/opt/usr/bin"
telegram_send_conf="/opt/etc/telegram-send.conf"
liters_threshold=2





export PATH="$PATH:/opt/bin:/opt/sbin:/opt/usr/bin:/opt/usr/sbin"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/opt/lib:/opt/usr/lib"

my_smartphone_mac=$(echo "$my_smartphone_mac" | awk '{print toupper($0)}')
if [ -z "$(iwinfo wlan0 assoclist | grep $my_smartphone_mac)" ] && [ -z "$(iwinfo wlan1 assoclist | grep $my_smartphone_mac)" ]; then
        amIpresent=0
else
        amIpresent=1
fi
echo "PRESENT:$amIpresent"
if [ $amIpresent -eq 0 ]; then
	#I'm out of home
	if [ ! -e $aigueselxpy_folder/waterflow_next_check ]; then
		next_fulldate_to_look=$(date '+%s')
		next_fulldate_to_look=$(($next_fulldate_to_look+7200))
		$(echo $next_fulldate_to_look > $aigueselxpy_folder/waterflow_next_check)
	fi
	next_fulldate_to_look=$(cat $aigueselxpy_folder/waterflow_next_check)
	next_day_to_look=$(date -d @$next_fulldate_to_look +'%d/%m/%Y')
	echo "NEXTDAYTOLOOK:$next_day_to_look"
	next_hour_to_look=$(date -d @$next_fulldate_to_look +'%H')
	echo "NEXT HOUR TO LOOK:$next_hour_to_look"
	water_data=$($bins_folder/python $aigueselxpy_folder/aigueselxpy.py -u $aigues_user:$aigues_password -f $next_day_to_look -t $next_day_to_look -j)
	water_value_at_hour=$(echo $water_data | $bins_folder/jq -r .[\"$next_day_to_look\"][$next_hour_to_look])
	if [ -n "$water_value_at_hour" ] && [ "$water_value_at_hour" -eq "$water_value_at_hour" ] 2>/dev/null; then
		#$water_value_at_hour contains a number
		if [ ! $water_value_at_hour -eq -1 ]; then
			#we have a water value
			while [ ! $water_value_at_hour -eq -1 ]
			do
				if [ -e $aigueselxpy_folder/waterflow_sensor.notices ] && [ -z $notices ]; then
					notices=$(cat $aigueselxpy_folder/waterflow_sensor.notices)
				elif [ -z $notices ]; then
					notices=0
				fi
				if [ -e $aigueselxpy_folder/waterflow_sensor.strikes ] && [ -z $strikes ]; then
					strikes=$(cat $aigueselxpy_folder/waterflow_sensor.strikes)
				elif [ -z $strikes ]; then
					strikes=0
				fi
				if [ $water_value_at_hour -gt $liters_threshold ] && [ $notices -lt 1 ]; then
					#warning, water leak!
					$bins_folder/telegram-send --config $telegram_send_conf "ALERTA: Fuga de agua en casa! Liters: $water_value_at_hour. Current json data: $water_data "
					$(echo $(($notices+1)) >  $aigueselxpy_folder/waterflow_sensor.notices)
				elif [ $water_value_at_hour -gt 0 ] && [ $notices -lt 1 ]; then
					#Some water detected 0<X<thresold. Check that is just a change in pipe pressure
					strikes=$(($strikes+1))
					$(echo $strikes >  $aigueselxpy_folder/waterflow_sensor.strikes)
					if [ $strikes -ge 3 ]; then
						$($bins_folder/telegram-send --config $telegram_send_conf "ALERTA: Fuga de agua en casa durante 3 o más horas consecutivas! Liters: $water_value_at_hour. Current json data: $water_data ")
						$(echo $(($notices+1)) > $aigueselxpy_folder/waterflow_sensor.notices)
					fi
				else
					echo "read 0, everything is OK"
				fi
				#point to next hour
				next_fulldate_to_look=$(($next_fulldate_to_look+3600))
			        next_day_to_look=$(date -d @$next_fulldate_to_look +'%d/%m/%Y')
 				echo "NEXTDAYTOLOOK:$next_day_to_look"
				next_hour_to_look=$(date -d @$next_fulldate_to_look +'%H')
				echo "NEXT HOUR TO LOOK:$next_hour_to_look"
				water_value_at_hour=$(echo $water_data | $bins_folder/jq -r .[\"$next_day_to_look\"][$next_hour_to_look])
			done
			#store new date to check for water
			echo "Set next check to $next_day_to_look at $next_hour_to_look h."
			$(echo $next_fulldate_to_look > $aigueselxpy_folder/waterflow_next_check)
		else
			#-1 value read. Just skip, no useful info for the moment
			echo "Read -1, skip,"
		fi
	else
		#$water_value_at_hour does not contains a number
		echo "ERROR: no water value at given hour could be read from aigueselx json data."
		echo ""
		echo "Waterdata: $water_data" 
		echo ""
		echo "Water_value at $next_hour_to_look: $water_value_at_hour"
	fi

else
	#I'm home, so delete flags
	if [ -e $aigueselxpy_folder/waterflow_next_check ]; then
		rm -rf  $aigueselxpy_folder/waterflow_next_check
	fi
	if [ -e $aigueselxpy_folder/waterflow_sensor.notices ]; then
		rm -rf  $aigueselxpy_folder/waterflow_sensor.notices
	fi
	if [ -e $aigueselxpy_folder/waterflow_sensor.strikes ]; then
		rm -rf  $aigueselxpy_folder/waterflow_sensor.strikes
	fi
fi



