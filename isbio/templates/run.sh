#!/bin/bash
# This script is called after container has extracted the archive.
# Place here any configuration required and call to the next script which should trigger the job.
#
# available_variables	default_value			description
# IN_FILE		'in.tar.xz'			file name to use for the input/job set archive
# OUT_FILE		'out.tar.xz'			file name to use fot the output/result archive
# NEXT_SH		$HOME'/run.sh'			the path of this file once extracted into the container
# AZURE_PY		$RES_FOLDER'/'$AZURE_STORAGE_FN	full path of the azure-storage python interface
# JOB_ID						the ID of the job, the only data passed on to the container (usually the md5 of the job archive)
# HOME			/root				home folder of the container. This is where all operations will happen
# HOSTNAME						the hostname of the container. usually the 12 first char of the docker-container id
# JAVA_HOME		/usr/java/jdk1.8.0_72/		the path to java in the container
# R_LIBS_USER 		/usr/lib/R/site-library t	the path to R in the container
# USER			root				current linux user inside the container. will ALWAYS be root
## BREEZE AUTO configuration
ABS_PATH=$job_full_path
export NEXT_SH=./'$run_job_sh'
## END OF BREEZE_CONFIG
export JOB_FOLDER=${HOME}${ABS_PATH}
export OUT_FILE_PATH=${HOME}'/'${OUT_FILE}
# FIXME move all that into container bootstrap script
END_C='\033[39m'
BLUE='\033[34m'
RED='\033[31m'
# Gros hack tout vilain # TODO finish
# ln -s $HOME /fs
# HOME/projects/breeze-ph2/db/
# /data-ph/breeze/db/datasets	/projects/breeze/db/datasets ro
# /data-ph/breeze/code			/projects/breeze/code ro
ln -s . /fs
ln -s /projects/breeze/ /projects/breeze-ph2
ln -s $HOME/projects/breeze-ph2/db/reports/ /projects/breeze/db/reports
# ln -s $HOME/projects/breeze $HOME/projects/breeze-ph2
ln -s $HOME/projects/breeze-ph2/ $HOME/projects/breeze
ln -s $HOME/ $HOME/fs
ln -s /projects/breeze/code/ $HOME/projects/breeze/code
# ln -s /projects/breeze/code/RMySqlLib /projects/breeze/RORALib
# ln -s /projects/breeze/code/RMySqlLib /projects/breeze/code/RORALib
# move to the job sub folder
echo -e ${BLUE}'cd '${JOB_FOLDER}''${END_C}
cd ${JOB_FOLDER}
# bootstrap
echo -e ${BLUE}'Running '${NEXT_SH}' ...'${END_C}
chmod ug+rx ${NEXT_SH}
${NEXT_SH} > ${NEXT_SH}.log 2>&1
EX=$?
# if [ $EX -eq 0 ];
# then
	# chown -R 1001:1001 *
	# preventive delete (suppressing errors)
	rm ${OUT_FILE_PATH} > /dev/null 2>&1
	echo -ne ${BLUE}'Creating archive '${OUT_FILE_PATH}' ...'${END_C} && echo 'done'
	tar  --no-acls --owner=breeze -jcf ${OUT_FILE_PATH} .
	${AZURE_PY} save # FIXME obsolete
	echo 'done'
# else
#	echo 'INTERUPTED, exit code was '${EX}
#fi
exit $EX
