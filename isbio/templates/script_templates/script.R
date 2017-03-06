breeze_now <- Sys.time() # time mesurement
#####################################
###	BREEZE SCRIPT: $tag_name
#####################################
# author: $author
# date : $date

#####################################
###        Header Section         ###
#####################################
$headers
#####################################
### Parameters Definition Section ###
#####################################
$gen_params
#####################################
###       Code Section            ###
#####################################
$body

#####################################
###	/END SCRIPT $tag_name /
#####################################
breeze_then <- Sys.time() # time mesurement
breeze_then - breeze_now  # time mesurement
