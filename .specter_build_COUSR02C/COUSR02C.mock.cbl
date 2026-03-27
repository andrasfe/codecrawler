      ******************************************************************        
      * Program     : COUSR02C.CBL
      * Application : CardDemo
      * Type        : CICS COBOL Program
      * Function    : Update a user in USRSEC file
      ******************************************************************
      * Copyright Amazon.com, Inc. or its affiliates.                   
      * All Rights Reserved.                                            
      *                                                                 
      * Licensed under the Apache License, Version 2.0 (the "License"). 
      * You may not use this file except in compliance with the License.
      * You may obtain a copy of the License at                         
      *                                                                 
      *    http://www.apache.org/licenses/LICENSE-2.0                   
      *                                                                 
      * Unless required by applicable law or agreed to in writing,      
      * software distributed under the License is distributed on an     
      * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,    
      * either express or implied. See the License for the specific     
      * language governing permissions and limitations under the License
      ****************************************************************** 
       IDENTIFICATION DIVISION.
       PROGRAM-ID. COUSR02C.
       AUTHOR.     AWS.

       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT MOCK-FILE ASSIGN TO
              'MOCKDATA'
              ORGANIZATION IS LINE SEQUENTIAL
              FILE STATUS IS MOCK-FILE-STATUS.

       DATA DIVISION.
      *----------------------------------------------------------------*
      *                     WORKING STORAGE SECTION
      *----------------------------------------------------------------*
       FILE SECTION.
       FD MOCK-FILE.
       01 MOCK-FILE-RECORD     PIC X(80).

       WORKING-STORAGE SECTION.
      * SPECTER PATCH: cobc-undefined fallback declarations
       01 RESP                           PIC X(256).
       01 RETURN-TO-PREV-SCREEN          PIC X(256).
       01 SEND-USRUPD-SCREEN             PIC X(256).
       01 SPECTER-CALL                   PIC X(256).
       01 SPECTER-TRACE                  PIC X(256).
       01 UPDATE-USER-INFO               PIC X(256).
       01 UPDATE-USER-SEC-FILE           PIC X(256).

      * SPECTER STUB: DFHAID (AID key values)
       01 DFHAID-CONSTANTS.
           05 DFHENTER        PIC X VALUE X'7D'.
           05 DFHCLEAR        PIC X VALUE X'6D'.
           05 DFHPA1          PIC X VALUE X'6C'.
           05 DFHPA2          PIC X VALUE X'6E'.
           05 DFHPA3          PIC X VALUE X'6B'.
           05 DFHPF1          PIC X VALUE X'F1'.
           05 DFHPF2          PIC X VALUE X'F2'.
           05 DFHPF3          PIC X VALUE X'F3'.
           05 DFHPF4          PIC X VALUE X'F4'.
           05 DFHPF5          PIC X VALUE X'F5'.
           05 DFHPF6          PIC X VALUE X'F6'.
           05 DFHPF7          PIC X VALUE X'F7'.
           05 DFHPF8          PIC X VALUE X'F8'.
           05 DFHPF9          PIC X VALUE X'F9'.
           05 DFHPF10         PIC X VALUE X'7A'.
           05 DFHPF11         PIC X VALUE X'7B'.
           05 DFHPF12         PIC X VALUE X'7C'.
           05 DFHPF13         PIC X VALUE X'C1'.
           05 DFHPF14         PIC X VALUE X'C2'.
           05 DFHPF15         PIC X VALUE X'C3'.
           05 DFHPF16         PIC X VALUE X'C4'.
           05 DFHPF17         PIC X VALUE X'C5'.
           05 DFHPF18         PIC X VALUE X'C6'.
           05 DFHPF19         PIC X VALUE X'C7'.
           05 DFHPF20         PIC X VALUE X'C8'.
           05 DFHPF21         PIC X VALUE X'C9'.
           05 DFHPF22         PIC X VALUE X'4A'.
           05 DFHPF23         PIC X VALUE X'4B'.
           05 DFHPF24         PIC X VALUE X'4C'.

      * SPECTER STUB: DFHBMSCA (BMS attributes)
       01 DFHBMSCA-CONSTANTS.
           05 DFHBMPRO        PIC X VALUE X'F0'.
           05 DFHBMUNP        PIC X VALUE X'C0'.
           05 DFHBMUNN        PIC X VALUE X'D0'.
           05 DFHBMPRF        PIC X VALUE X'61'.
           05 DFHBMASF        PIC X VALUE X'C1'.
           05 DFHBMASK        PIC X VALUE X'F0'.
           05 DFHBMFSE        PIC X VALUE X'C8'.
           05 DFHRED          PIC X VALUE X'F2'.
           05 DFHBLUE         PIC X VALUE X'F4'.
           05 DFHGREEN        PIC X VALUE X'F5'.
           05 DFHWHITE        PIC X VALUE X'F7'.
           05 DFHYELLO        PIC X VALUE X'F6'.
           05 DFHTURQ         PIC X VALUE X'F1'.
           05 DFHPINK         PIC X VALUE X'F3'.
           05 DFHDFCOL        PIC X VALUE X'00'.
           05 DFHNEUTR        PIC X VALUE X'00'.
           05 DFHBMDAR        PIC X VALUE X'0C'.
           05 DFHBMBRY        PIC X VALUE X'F0'.

      * SPECTER STUB: EIB (Execute Interface Block)
       01 DFHEIBLK.
           05 EIBTIME         PIC S9(7) COMP-3 VALUE 0.
           05 EIBDATE         PIC S9(7) COMP-3 VALUE 0.
           05 EIBTRNID        PIC X(4) VALUE SPACES.
           05 EIBTASKN        PIC S9(7) COMP-3 VALUE 0.
           05 EIBTRMID        PIC X(4) VALUE SPACES.
           05 EIBCPOSN        PIC S9(4) COMP VALUE 0.
           05 EIBCALEN        PIC S9(4) COMP VALUE 0.
           05 EIBAID          PIC X VALUE SPACES.
           05 EIBFN           PIC X(2) VALUE SPACES.
           05 EIBRCODE        PIC X(6) VALUE SPACES.
           05 EIBDS           PIC X(8) VALUE SPACES.
           05 EIBREQID        PIC X(8) VALUE SPACES.
           05 EIBRSRCE        PIC X(8) VALUE SPACES.
           05 EIBSYNC         PIC X VALUE SPACES.
           05 EIBFREE         PIC X VALUE SPACES.
           05 EIBRECV         PIC X VALUE SPACES.
           05 EIBSIG          PIC X VALUE SPACES.
           05 EIBCONF         PIC X VALUE SPACES.
           05 EIBERR          PIC X VALUE SPACES.
           05 EIBERRCD        PIC X(4) VALUE SPACES.
           05 EIBSYNRB        PIC X VALUE SPACES.
           05 EIBNODAT        PIC X VALUE SPACES.
           05 EIBRESP         PIC S9(8) COMP VALUE 0.
           05 EIBRESP2        PIC S9(8) COMP VALUE 0.

      * SPECTER MOCK INFRASTRUCTURE
       01 MOCK-RECORD.
           05 MOCK-OP-KEY        PIC X(30).
           05 MOCK-ALPHA-STATUS  PIC X(20).
           05 MOCK-NUM-STATUS    PIC S9(09).
           05 MOCK-FILLER        PIC X(21).
       01 MOCK-FILE-STATUS      PIC XX VALUE '00'.

      * SPECTER COMMON STUBS
       01 DIBSTAT               PIC X(02) VALUE SPACES.
       01 SQLCODE               PIC S9(09) COMP VALUE 0.


       01 WS-VARIABLES.
         05 WS-PGMNAME                 PIC X(08) VALUE 'COUSR02C'.
         05 WS-TRANID                  PIC X(04) VALUE 'CU02'.
         05 WS-MESSAGE                 PIC X(80) VALUE SPACES.
         05 WS-USRSEC-FILE             PIC X(08) VALUE 'USRSEC  '.
         05 WS-ERR-FLG                 PIC X(01) VALUE 'N'.
           88 ERR-FLG-ON                         VALUE 'Y'.
           88 ERR-FLG-OFF                        VALUE 'N'.
         05 WS-RESP-CD                 PIC S9(09) COMP VALUE ZEROS.
         05 WS-REAS-CD                 PIC S9(09) COMP VALUE ZEROS.
         05 WS-USR-MODIFIED            PIC X(01) VALUE 'N'.
           88 USR-MODIFIED-YES                   VALUE 'Y'.
           88 USR-MODIFIED-NO                    VALUE 'N'.

      * SPECTER: COPY COCOM01Y inlined from COCOM01Y.cpy
      ******************************************************************
      * Communication area for CardDemo application programs
      ******************************************************************
      * Copyright Amazon.com, Inc. or its affiliates.                   
      * All Rights Reserved.                                            
      *                                                                 
      * Licensed under the Apache License, Version 2.0 (the "License"). 
      * You may not use this file except in compliance with the License.
      * You may obtain a copy of the License at                         
      *                                                                 
      *    http://www.apache.org/licenses/LICENSE-2.0                   
      *                                                                 
      * Unless required by applicable law or agreed to in writing,      
      * software distributed under the License is distributed on an     
      * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,    
      * either express or implied. See the License for the specific     
      * language governing permissions and limitations under the License
      ****************************************************************** 
       01 CARDDEMO-COMMAREA.
          05 CDEMO-GENERAL-INFO.
             10 CDEMO-FROM-TRANID             PIC X(04).
             10 CDEMO-FROM-PROGRAM            PIC X(08).
             10 CDEMO-TO-TRANID               PIC X(04).
             10 CDEMO-TO-PROGRAM              PIC X(08).
             10 CDEMO-USER-ID                 PIC X(08).
             10 CDEMO-USER-TYPE               PIC X(01).
                88 CDEMO-USRTYP-ADMIN         VALUE 'A'.
                88 CDEMO-USRTYP-USER          VALUE 'U'.
             10 CDEMO-PGM-CONTEXT             PIC 9(01).
                88 CDEMO-PGM-ENTER            VALUE 0.
                88 CDEMO-PGM-REENTER          VALUE 1.
          05 CDEMO-CUSTOMER-INFO.
             10 CDEMO-CUST-ID                 PIC 9(09).
             10 CDEMO-CUST-FNAME              PIC X(25).
             10 CDEMO-CUST-MNAME              PIC X(25).
             10 CDEMO-CUST-LNAME              PIC X(25).
          05 CDEMO-ACCOUNT-INFO.
             10 CDEMO-ACCT-ID                 PIC 9(11).
             10 CDEMO-ACCT-STATUS             PIC X(01).
          05 CDEMO-CARD-INFO.
             10 CDEMO-CARD-NUM                PIC 9(16).
          05 CDEMO-MORE-INFO.
             10  CDEMO-LAST-MAP               PIC X(7).
             10  CDEMO-LAST-MAPSET            PIC X(7).
      *
      * Ver: CardDemo_v1.0-15-g27d6c6f-68 Date: 2022-07-19 23:15:57 CDT
      *
          05 CDEMO-CU02-INFO.
             10 CDEMO-CU02-USRID-FIRST     PIC X(08).
             10 CDEMO-CU02-USRID-LAST      PIC X(08).
             10 CDEMO-CU02-PAGE-NUM        PIC 9(08).
             10 CDEMO-CU02-NEXT-PAGE-FLG   PIC X(01) VALUE 'N'.
                88 NEXT-PAGE-YES                     VALUE 'Y'.
                88 NEXT-PAGE-NO                      VALUE 'N'.
             10 CDEMO-CU02-USR-SEL-FLG     PIC X(01).
             10 CDEMO-CU02-USR-SELECTED    PIC X(08).

      * SPECTER: COPY COUSR02 (not found)

      * SPECTER: COPY COTTL01Y inlined from COTTL01Y.cpy
      ******************************************************************
      * Copyright Amazon.com, Inc. or its affiliates.                   
      * All Rights Reserved.                                            
      *                                                                 
      * Licensed under the Apache License, Version 2.0 (the "License"). 
      * You may not use this file except in compliance with the License.
      * You may obtain a copy of the License at                         
      *                                                                 
      *    http://www.apache.org/licenses/LICENSE-2.0                   
      *                                                                 
      * Unless required by applicable law or agreed to in writing,      
      * software distributed under the License is distributed on an     
      * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,    
      * either express or implied. See the License for the specific     
      * language governing permissions and limitations under the License
      ****************************************************************** 
       01 CCDA-SCREEN-TITLE.
         05 CCDA-TITLE01    PIC X(40) VALUE
            '      AWS Mainframe Modernization       '.
         05 CCDA-TITLE02    PIC X(40) VALUE
      *     '  Credit Card Demo Application (CCDA)   '.
            '              CardDemo                  '.
         05 CCDA-THANK-YOU  PIC X(40) VALUE
            'Thank you for using CCDA application... '.
      *
      * Ver: CardDemo_v1.0-15-g27d6c6f-68 Date: 2022-07-19 23:15:58 CDT
      *
      * SPECTER: COPY CSDAT01Y inlined from CSDAT01Y.cpy
      ******************************************************************
      * Copyright Amazon.com, Inc. or its affiliates.                   
      * All Rights Reserved.                                            
      *                                                                 
      * Licensed under the Apache License, Version 2.0 (the "License"). 
      * You may not use this file except in compliance with the License.
      * You may obtain a copy of the License at                         
      *                                                                 
      *    http://www.apache.org/licenses/LICENSE-2.0                   
      *                                                                 
      * Unless required by applicable law or agreed to in writing,      
      * software distributed under the License is distributed on an     
      * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,    
      * either express or implied. See the License for the specific     
      * language governing permissions and limitations under the License
      ****************************************************************** 
       01 WS-DATE-TIME.
         05 WS-CURDATE-DATA.
           10  WS-CURDATE.
             15  WS-CURDATE-YEAR         PIC 9(04).
             15  WS-CURDATE-MONTH        PIC 9(02).
             15  WS-CURDATE-DAY          PIC 9(02).
           10 WS-CURDATE-N REDEFINES WS-CURDATE PIC 9(08).
           10  WS-CURTIME.
             15  WS-CURTIME-HOURS        PIC 9(02).
             15  WS-CURTIME-MINUTE       PIC 9(02).
             15  WS-CURTIME-SECOND       PIC 9(02).
             15  WS-CURTIME-MILSEC       PIC 9(02).
           10 WS-CURTIME-N REDEFINES WS-CURTIME PIC 9(08).
         05 WS-CURDATE-MM-DD-YY.
           10  WS-CURDATE-MM             PIC 9(02).
           10  FILLER                    PIC X(01) VALUE '/'.
           10  WS-CURDATE-DD             PIC 9(02).
           10  FILLER                    PIC X(01) VALUE '/'.
           10  WS-CURDATE-YY             PIC 9(02).
         05 WS-CURTIME-HH-MM-SS.
           10  WS-CURTIME-HH             PIC 9(02).
           10  FILLER                    PIC X(01) VALUE ':'.
           10  WS-CURTIME-MM             PIC 9(02).
           10  FILLER                    PIC X(01) VALUE ':'.
           10  WS-CURTIME-SS             PIC 9(02).
         05 WS-TIMESTAMP.
           10  WS-TIMESTAMP-DT-YYYY      PIC 9(04).
           10  FILLER                    PIC X(01) VALUE '-'.
           10  WS-TIMESTAMP-DT-MM        PIC 9(02).
           10  FILLER                    PIC X(01) VALUE '-'.
           10  WS-TIMESTAMP-DT-DD        PIC 9(02).
           10  FILLER                    PIC X(01) VALUE ' '.
           10  WS-TIMESTAMP-TM-HH        PIC 9(02).
           10  FILLER                    PIC X(01) VALUE ':'.
           10  WS-TIMESTAMP-TM-MM        PIC 9(02).
           10  FILLER                    PIC X(01) VALUE ':'.
           10  WS-TIMESTAMP-TM-SS        PIC 9(02).
           10  FILLER                    PIC X(01) VALUE '.'.
           10  WS-TIMESTAMP-TM-MS6       PIC 9(06).
      *
      * Ver: CardDemo_v1.0-15-g27d6c6f-68 Date: 2022-07-19 23:15:58 CDT
      *
      * SPECTER: COPY CSMSG01Y inlined from CSMSG01Y.cpy
      ******************************************************************
      * Copyright Amazon.com, Inc. or its affiliates.                   
      * All Rights Reserved.                                            
      *                                                                 
      * Licensed under the Apache License, Version 2.0 (the "License"). 
      * You may not use this file except in compliance with the License.
      * You may obtain a copy of the License at                         
      *                                                                 
      *    http://www.apache.org/licenses/LICENSE-2.0                   
      *                                                                 
      * Unless required by applicable law or agreed to in writing,      
      * software distributed under the License is distributed on an     
      * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,    
      * either express or implied. See the License for the specific     
      * language governing permissions and limitations under the License
      ****************************************************************** 
       01 CCDA-COMMON-MESSAGES.
         05 CCDA-MSG-THANK-YOU         PIC X(50) VALUE
              'Thank you for using CardDemo application...      '.
         05 CCDA-MSG-INVALID-KEY       PIC X(50) VALUE
              'Invalid key pressed. Please see below...         '.
      *
      * Ver: CardDemo_v1.0-15-g27d6c6f-68 Date: 2022-07-19 23:15:58 CDT
      *
      * SPECTER: COPY CSUSR01Y inlined from CSUSR01Y.cpy
      ******************************************************************
      * Copyright Amazon.com, Inc. or its affiliates.                   
      * All Rights Reserved.                                            
      *                                                                 
      * Licensed under the Apache License, Version 2.0 (the "License"). 
      * You may not use this file except in compliance with the License.
      * You may obtain a copy of the License at                         
      *                                                                 
      *    http://www.apache.org/licenses/LICENSE-2.0                   
      *                                                                 
      * Unless required by applicable law or agreed to in writing,      
      * software distributed under the License is distributed on an     
      * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,    
      * either express or implied. See the License for the specific     
      * language governing permissions and limitations under the License
      ****************************************************************** 
       01 SEC-USER-DATA.
         05 SEC-USR-ID                 PIC X(08).
         05 SEC-USR-FNAME              PIC X(20).
         05 SEC-USR-LNAME              PIC X(20).
         05 SEC-USR-PWD                PIC X(08).
         05 SEC-USR-TYPE               PIC X(01).
         05 SEC-USR-FILLER             PIC X(23).
       01  DFHCOMMAREA.
         05  LK-COMMAREA                           PIC X(01)
             OCCURS 1 TO 32767 TIMES DEPENDING ON EIBCALEN.
      *
      * Ver: CardDemo_v1.0-15-g27d6c6f-68 Date: 2022-07-19 23:15:59 CDT
      *

      * SPECTER: COPY DFHAID (not found)
      * SPECTER: COPY DFHBMSCA (not found)

      *----------------------------------------------------------------*
      *                        LINKAGE SECTION
      *----------------------------------------------------------------*
      *LINKAGE SECTION.
      *01  DFHCOMMAREA.
      *  05  LK-COMMAREA                           PIC X(01)
      *      OCCURS 1 TO 32767 TIMES DEPENDING ON EIBCALEN.

      *----------------------------------------------------------------*
      *                       PROCEDURE DIVISION
      *----------------------------------------------------------------*
       PROCEDURE DIVISION.
      *MAIN-PARA.
           CONTINUE.
      *    DISPLAY 'SPECTER-TRACE:MAIN-PARA'.

      *    SET ERR-FLG-OFF     TO TRUE
      *    SET USR-MODIFIED-NO TO TRUE

      *    MOVE SPACES TO WS-MESSAGE
      *                   ERRMSGO OF COUSR2AO

      *    IF EIBCALEN = 0
      *        MOVE 'COSGN00C' TO CDEMO-TO-PROGRAM
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=RETURN-TO-PREV-SCREEN'.
      *        PERFORM RETURN-TO-PREV-SCREEN
      *    ELSE
      *        MOVE DFHCOMMAREA(1:EIBCALEN) TO CARDDEMO-COMMAREA
      *        IF NOT CDEMO-PGM-REENTER
      *            SET CDEMO-PGM-REENTER    TO TRUE
      *            MOVE LOW-VALUES          TO COUSR2AO
      *            MOVE -1       TO USRIDINL OF COUSR2AI
      *            IF CDEMO-CU02-USR-SELECTED NOT =
      *                                       SPACES AND LOW-VALUES
      *                MOVE CDEMO-CU02-USR-SELECTED TO
      *                     USRIDINI OF COUSR2AI
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=PROCESS-ENTER-KEY'.
      *                PERFORM PROCESS-ENTER-KEY
      *            END-IF
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=SEND-USRUPD-SCREEN'.
      *            PERFORM SEND-USRUPD-SCREEN
      *        ELSE
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=RECEIVE-USRUPD-SCREEN'.
      *            PERFORM RECEIVE-USRUPD-SCREEN
      *            EVALUATE EIBAID
      *                WHEN DFHENTER
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=PROCESS-ENTER-KEY'.
      *                    PERFORM PROCESS-ENTER-KEY
      *                WHEN DFHPF3
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=UPDATE-USER-INFO'.
      *                    PERFORM UPDATE-USER-INFO
      *                    IF CDEMO-FROM-PROGRAM = SPACES OR LOW-VALUES
      *                        MOVE 'COADM01C' TO CDEMO-TO-PROGRAM
      *                    ELSE
      *                        MOVE CDEMO-FROM-PROGRAM TO
      *                        CDEMO-TO-PROGRAM
      *                    END-IF
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=RETURN-TO-PREV-SCREEN'.
      *                    PERFORM RETURN-TO-PREV-SCREEN
      *                WHEN DFHPF4
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=CLEAR-CURRENT-SCREEN'.
      *                    PERFORM CLEAR-CURRENT-SCREEN
      *                WHEN DFHPF5
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=UPDATE-USER-INFO'.
      *                    PERFORM UPDATE-USER-INFO
      *                WHEN DFHPF12
      *                    MOVE 'COADM01C' TO CDEMO-TO-PROGRAM
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=RETURN-TO-PREV-SCREEN'.
      *                    PERFORM RETURN-TO-PREV-SCREEN
      *                WHEN OTHER
      *                    MOVE 'Y'                       TO WS-ERR-FLG
      *                    MOVE CCDA-MSG-INVALID-KEY      TO WS-MESSAGE
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=SEND-USRUPD-SCREEN'.
      *                    PERFORM SEND-USRUPD-SCREEN
      *            END-EVALUATE
      *        END-IF
      *    END-IF

      *    EXEC CICS RETURN
      *              TRANSID (WS-TRANID)
      *              COMMAREA (CARDDEMO-COMMAREA)
      *    END-EXEC.
      *    DISPLAY 'SPECTER-CICS:RETURN'
      *    GO TO SPECTER-EXIT-PARA.

      *----------------------------------------------------------------*
      *                      PROCESS-ENTER-KEY
      *----------------------------------------------------------------*
       PROCESS-ENTER-KEY.
           DISPLAY 'SPECTER-TRACE:PROCESS-ENTER-KEY'.
      *    CONTINUE.

      *    EVALUATE TRUE
      *        WHEN USRIDINI OF COUSR2AI = SPACES OR LOW-VALUES
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'User ID can NOT be empty...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO USRIDINL OF COUSR2AI
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=SEND-USRUPD-SCREEN'.
      *            PERFORM SEND-USRUPD-SCREEN
      *        WHEN OTHER
      *            MOVE -1       TO USRIDINL OF COUSR2AI
      *            CONTINUE
      *    END-EVALUATE

      *    IF NOT ERR-FLG-ON
      *        MOVE SPACES      TO FNAMEI   OF COUSR2AI
      *                            LNAMEI   OF COUSR2AI
      *                            PASSWDI  OF COUSR2AI
      *                            USRTYPEI OF COUSR2AI
      *        MOVE USRIDINI  OF COUSR2AI TO SEC-USR-ID
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=READ-USER-SEC-FILE'.
      *        PERFORM READ-USER-SEC-FILE
      *    END-IF.

      *    IF NOT ERR-FLG-ON
      *        MOVE SEC-USR-FNAME      TO FNAMEI    OF COUSR2AI
      *        MOVE SEC-USR-LNAME      TO LNAMEI    OF COUSR2AI
      *        MOVE SEC-USR-PWD        TO PASSWDI   OF COUSR2AI
      *        MOVE SEC-USR-TYPE       TO USRTYPEI  OF COUSR2AI
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=SEND-USRUPD-SCREEN'.
      *        PERFORM SEND-USRUPD-SCREEN
      *    END-IF.

      *----------------------------------------------------------------*
      *                      UPDATE-USER-INFO
      *----------------------------------------------------------------*
      *UPDATE-USER-INFO.
           CONTINUE.

      *    EVALUATE TRUE
      *        WHEN USRIDINI OF COUSR2AI = SPACES OR LOW-VALUES
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'User ID can NOT be empty...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO USRIDINL OF COUSR2AI
      *    DISPLAY 'SPECTER-CALL:FROM=UPDATE-USER-INFO:TO=SEND-USRUPD-SCREEN'.
      *            PERFORM SEND-USRUPD-SCREEN
      *        WHEN FNAMEI OF COUSR2AI = SPACES OR LOW-VALUES
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'First Name can NOT be empty...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO FNAMEL OF COUSR2AI
      *    DISPLAY 'SPECTER-CALL:FROM=UPDATE-USER-INFO:TO=SEND-USRUPD-SCREEN'.
      *            PERFORM SEND-USRUPD-SCREEN
      *        WHEN LNAMEI OF COUSR2AI = SPACES OR LOW-VALUES
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Last Name can NOT be empty...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO LNAMEL OF COUSR2AI
      *    DISPLAY 'SPECTER-CALL:FROM=UPDATE-USER-INFO:TO=SEND-USRUPD-SCREEN'.
      *            PERFORM SEND-USRUPD-SCREEN
      *        WHEN PASSWDI OF COUSR2AI = SPACES OR LOW-VALUES
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Password can NOT be empty...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO PASSWDL OF COUSR2AI
      *    DISPLAY 'SPECTER-CALL:FROM=UPDATE-USER-INFO:TO=SEND-USRUPD-SCREEN'.
      *            PERFORM SEND-USRUPD-SCREEN
      *        WHEN USRTYPEI OF COUSR2AI = SPACES OR LOW-VALUES
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'User Type can NOT be empty...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO USRTYPEL OF COUSR2AI
      *    DISPLAY 'SPECTER-CALL:FROM=UPDATE-USER-INFO:TO=SEND-USRUPD-SCREEN'.
      *            PERFORM SEND-USRUPD-SCREEN
      *        WHEN OTHER
      *            MOVE -1       TO FNAMEL OF COUSR2AI
      *            CONTINUE
      *    END-EVALUATE

      *    IF NOT ERR-FLG-ON
      *        MOVE USRIDINI  OF COUSR2AI TO SEC-USR-ID
      *    DISPLAY 'SPECTER-CALL:FROM=UPDATE-USER-INFO:TO=READ-USER-SEC-FILE'.
      *        PERFORM READ-USER-SEC-FILE

      *        IF FNAMEI  OF COUSR2AI NOT = SEC-USR-FNAME
      *            MOVE FNAMEI   OF COUSR2AI TO SEC-USR-FNAME
      *            SET USR-MODIFIED-YES TO TRUE
      *        END-IF
      *        IF LNAMEI  OF COUSR2AI NOT = SEC-USR-LNAME
      *            MOVE LNAMEI   OF COUSR2AI TO SEC-USR-LNAME
      *            SET USR-MODIFIED-YES TO TRUE
      *        END-IF
      *        IF PASSWDI  OF COUSR2AI NOT = SEC-USR-PWD
      *            MOVE PASSWDI  OF COUSR2AI TO SEC-USR-PWD
      *            SET USR-MODIFIED-YES TO TRUE
      *        END-IF
      *        IF USRTYPEI  OF COUSR2AI NOT = SEC-USR-TYPE
      *            MOVE USRTYPEI OF COUSR2AI TO SEC-USR-TYPE
      *            SET USR-MODIFIED-YES TO TRUE
      *        END-IF

      *        IF USR-MODIFIED-YES
      *    DISPLAY 'SPECTER-CALL:FROM=UPDATE-USER-INFO:TO=UPDATE-USER-SEC-FILE'.
      *            PERFORM UPDATE-USER-SEC-FILE
      *        ELSE
      *            MOVE 'Please modify to update ...' TO
      *                            WS-MESSAGE
      *            MOVE DFHRED       TO ERRMSGC  OF COUSR2AO
      *    DISPLAY 'SPECTER-CALL:FROM=UPDATE-USER-INFO:TO=SEND-USRUPD-SCREEN'.
      *            PERFORM SEND-USRUPD-SCREEN
      *        END-IF

      *    END-IF.

      *----------------------------------------------------------------*
      *                      RETURN-TO-PREV-SCREEN
      *----------------------------------------------------------------*
      *RETURN-TO-PREV-SCREEN.
           CONTINUE.

      *    IF CDEMO-TO-PROGRAM = LOW-VALUES OR SPACES
      *        MOVE 'COSGN00C' TO CDEMO-TO-PROGRAM
      *    END-IF
      *    MOVE WS-TRANID    TO CDEMO-FROM-TRANID
      *    MOVE WS-PGMNAME   TO CDEMO-FROM-PROGRAM
      *    MOVE ZEROS        TO CDEMO-PGM-CONTEXT
      *    EXEC CICS
      *        XCTL PROGRAM(CDEMO-TO-PROGRAM)
      *        COMMAREA(CARDDEMO-COMMAREA)
      *    END-EXEC.
      *    DISPLAY 'SPECTER-CICS:XCTL:CDEMO-TO-PROGRAM'
      *    GO TO SPECTER-EXIT-PARA.

      *----------------------------------------------------------------*
      *                      SEND-USRUPD-SCREEN
      *----------------------------------------------------------------*
      *SEND-USRUPD-SCREEN.
           CONTINUE.

      *    DISPLAY 'SPECTER-CALL:FROM=SEND-USRUPD-SCREEN:TO=POPULATE-HEADER-INFO'.
      *    PERFORM POPULATE-HEADER-INFO

      *    MOVE WS-MESSAGE TO ERRMSGO OF COUSR2AO

      *    EXEC CICS SEND
      *              MAP('COUSR2A')
      *              MAPSET('COUSR02')
      *              FROM(COUSR2AO)
      *              ERASE
      *              CURSOR
      *    END-EXEC.
      *    DISPLAY 'SPECTER-MOCK:CICS-SEND'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ.

      *----------------------------------------------------------------*
      *                      RECEIVE-USRUPD-SCREEN
      *----------------------------------------------------------------*
       RECEIVE-USRUPD-SCREEN.
           DISPLAY 'SPECTER-TRACE:RECEIVE-USRUPD-SCREEN'.

      *    EXEC CICS RECEIVE
      *              MAP('COUSR2A')
      *              MAPSET('COUSR02')
      *              INTO(COUSR2AI)
      *              RESP(WS-RESP-CD)
      *              RESP2(WS-REAS-CD)
      *    END-EXEC.
           DISPLAY 'SPECTER-MOCK:CICS-RECEIVE'
           READ MOCK-FILE INTO MOCK-RECORD
              AT END
                MOVE '00' TO MOCK-ALPHA-STATUS
                MOVE 0 TO MOCK-NUM-STATUS
           END-READ
           MOVE MOCK-ALPHA-STATUS(1:1) TO EIBAID
           MOVE MOCK-NUM-STATUS TO WS-RESP-CD
           MOVE 0 TO WS-REAS-CD.

      *----------------------------------------------------------------*
      *                      POPULATE-HEADER-INFO
      *----------------------------------------------------------------*
       POPULATE-HEADER-INFO.
           DISPLAY 'SPECTER-TRACE:POPULATE-HEADER-INFO'.
           CONTINUE.

      *    MOVE FUNCTION CURRENT-DATE  TO WS-CURDATE-DATA

      *    MOVE CCDA-TITLE01           TO TITLE01O OF COUSR2AO
      *    MOVE CCDA-TITLE02           TO TITLE02O OF COUSR2AO
      *    MOVE WS-TRANID              TO TRNNAMEO OF COUSR2AO
      *    MOVE WS-PGMNAME             TO PGMNAMEO OF COUSR2AO

      *    MOVE WS-CURDATE-MONTH       TO WS-CURDATE-MM
      *    MOVE WS-CURDATE-DAY         TO WS-CURDATE-DD
      *    MOVE WS-CURDATE-YEAR(3:2)   TO WS-CURDATE-YY

      *    MOVE WS-CURDATE-MM-DD-YY    TO CURDATEO OF COUSR2AO

      *    MOVE WS-CURTIME-HOURS       TO WS-CURTIME-HH
      *    MOVE WS-CURTIME-MINUTE      TO WS-CURTIME-MM
      *    MOVE WS-CURTIME-SECOND      TO WS-CURTIME-SS

      *    MOVE WS-CURTIME-HH-MM-SS    TO CURTIMEO OF COUSR2AO.

      *----------------------------------------------------------------*
      *                      READ-USER-SEC-FILE
      *----------------------------------------------------------------*
      *S-S-S-S-S-S-S-S-READ-USER-SEC-.        
           CONTINUE.

      *    EXEC CICS READ
      *         DATASET   (WS-USRSEC-FILE)
      *         INTO      (SEC-USER-DATA)
      *         LENGTH    (LENGTH OF SEC-USER-DATA)
      *         RIDFLD    (SEC-USR-ID)
      *         KEYLENGTH (LENGTH OF SEC-USR-ID)
      *         UPDATE
      *         RESP      (WS-RESP-CD)
      *         RESP2     (WS-REAS-CD)
      *    END-EXEC.
      *    DISPLAY 'SPECTER-MOCK:CICS-READ'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ
      *    MOVE MOCK-NUM-STATUS TO WS-RESP-CD
      *    MOVE 0 TO WS-REAS-CD.

      *    EVALUATE WS-RESP-CD
      *        WHEN 0
      *            CONTINUE
      *            MOVE 'Press PF5 key to save your updates ...' TO
      *                            WS-MESSAGE
      *            MOVE DFHNEUTR       TO ERRMSGC  OF COUSR2AO
      *    DISPLAY 'SPECTER-CALL:FROM=READ-USER-SEC-FILE:TO=SEND-USRUPD-SCREEN'.
      *            PERFORM SEND-USRUPD-SCREEN
      *        WHEN 13
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'User ID NOT found...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO USRIDINL OF COUSR2AI
      *    DISPLAY 'SPECTER-CALL:FROM=READ-USER-SEC-FILE:TO=SEND-USRUPD-SCREEN'.
      *            PERFORM SEND-USRUPD-SCREEN
      *        WHEN OTHER
      *            DISPLAY 'RESP:' WS-RESP-CD 'REAS:' WS-REAS-CD
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Unable to lookup User...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO FNAMEL OF COUSR2AI
      *    DISPLAY 'SPECTER-CALL:FROM=READ-USER-SEC-FILE:TO=SEND-USRUPD-SCREEN'.
      *            PERFORM SEND-USRUPD-SCREEN
      *    END-EVALUATE.

      *----------------------------------------------------------------*
      *                      UPDATE-USER-SEC-FILE
      *----------------------------------------------------------------*
      *UPDATE-USER-SEC-FILE.
      *    CONTINUE.

      *    EXEC CICS REWRITE
      *         DATASET   (WS-USRSEC-FILE)
      *         FROM      (SEC-USER-DATA)
      *         LENGTH    (LENGTH OF SEC-USER-DATA)
      *         RESP      (WS-RESP-CD)
      *         RESP2     (WS-REAS-CD)
      *    END-EXEC.
      *    DISPLAY 'SPECTER-MOCK:CICS'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ
      *    MOVE MOCK-NUM-STATUS TO WS-RESP-CD
      *    MOVE 0 TO WS-REAS-CD.

      *    EVALUATE WS-RESP-CD
      *        WHEN 0
      *            MOVE SPACES             TO WS-MESSAGE
      *            MOVE DFHGREEN           TO ERRMSGC  OF COUSR2AO
      *            STRING 'User '     DELIMITED BY SIZE
      *                   SEC-USR-ID  DELIMITED BY SPACE
      *                   ' has been updated ...' DELIMITED BY SIZE
      *              INTO WS-MESSAGE
      *    DISPLAY 'SPECTER-CALL:FROM=UPDATE-USER-SEC-FILE:TO=SEND-USRUPD-SCREEN'.
      *            PERFORM SEND-USRUPD-SCREEN
      *        WHEN 13
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'User ID NOT found...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO USRIDINL OF COUSR2AI
      *    DISPLAY 'SPECTER-CALL:FROM=UPDATE-USER-SEC-FILE:TO=SEND-USRUPD-SCREEN'.
      *            PERFORM SEND-USRUPD-SCREEN
      *        WHEN OTHER
      *            DISPLAY 'RESP:' WS-RESP-CD 'REAS:' WS-REAS-CD
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Unable to Update User...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO FNAMEL OF COUSR2AI
      *    DISPLAY 'SPECTER-CALL:FROM=UPDATE-USER-SEC-FILE:TO=SEND-USRUPD-SCREEN'.
      *            PERFORM SEND-USRUPD-SCREEN
      *    END-EVALUATE.

      *----------------------------------------------------------------*
      *                      CLEAR-CURRENT-SCREEN
      *----------------------------------------------------------------*
       CLEAR-CURRENT-SCREEN.
           DISPLAY 'SPECTER-TRACE:CLEAR-CURRENT-SCREEN'.
           CONTINUE.

      *    DISPLAY 'SPECTER-CALL:FROM=CLEAR-CURRENT-SCREEN:TO=INITIALIZE-ALL-FIELDS'.
      *    PERFORM INITIALIZE-ALL-FIELDS.
      *    DISPLAY 'SPECTER-CALL:FROM=CLEAR-CURRENT-SCREEN:TO=SEND-USRUPD-SCREEN'.
      *    PERFORM SEND-USRUPD-SCREEN.

      *----------------------------------------------------------------*
      *                      INITIALIZE-ALL-FIELDS
      *----------------------------------------------------------------*
       INITIALIZE-ALL-FIELDS.
      *    DISPLAY 'SPECTER-TRACE:INITIALIZE-ALL-FIELDS'.

      *    MOVE -1              TO USRIDINL OF COUSR2AI
      *    MOVE SPACES          TO USRIDINI OF COUSR2AI
      *                            FNAMEI   OF COUSR2AI
      *                            LNAMEI   OF COUSR2AI
           CONTINUE.
      *                            USRTYPEI OF COUSR2AI
      *                            WS-MESSAGE.
      *
      * Ver: CardDemo_v1.0-15-g27d6c6f-68 Date: 2022-07-19 23:12:34 CDT
      *

      * SPECTER: exit paragraph for CICS RETURN/XCTL

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-READ-USER-SE. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-READ-USER-SE'.
           EXIT.
       SPECTER-EXIT-PARA.
           CLOSE MOCK-FILE
           STOP RUN.
