      ******************************************************************        
      * Program     : COSGN00C.CBL
      * Application : CardDemo
      * Type        : CICS COBOL Program
      * Function    : Signon Screen for the CardDemo Application
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
       PROGRAM-ID. COSGN00C.
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
       01 SPECTER-MOCK                   PIC X(256).
      * SPECTER PATCH: cobc-undefined fallback declarations
       01 COADM01C                       PIC X(256).
       01 COMEN01C                       PIC X(256).
       01 COSGN0AO                       PIC X(256).
       01 ENTER                          PIC X(256).
       01 PLEASE                         PIC X(256).
       01 SPECTER-TRACE                  PIC X(256).

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
         05 WS-PGMNAME                 PIC X(08) VALUE 'COSGN00C'.
         05 WS-TRANID                  PIC X(04) VALUE 'CC00'.
         05 WS-MESSAGE                 PIC X(80) VALUE SPACES.
         05 WS-USRSEC-FILE             PIC X(08) VALUE 'USRSEC  '.
         05 WS-ERR-FLG                 PIC X(01) VALUE 'N'.
           88 ERR-FLG-ON                         VALUE 'Y'.
           88 ERR-FLG-OFF                        VALUE 'N'.
         05 WS-RESP-CD                 PIC S9(09) COMP VALUE ZEROS.
         05 WS-REAS-CD                 PIC S9(09) COMP VALUE ZEROS.
         05 WS-USER-ID                 PIC X(08).
         05 WS-USER-PWD                PIC X(08).

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

      * SPECTER: COPY COSGN00 (not found)

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
      * SPECTER: COPY DFHATTR (not found)

      *----------------------------------------------------------------*
      *                        LINKAGE SECTION
      *----------------------------------------------------------------*
      *LINKAGE SECTION.
      *01  DFHCOMMAREA.
      *  05  LK-COMMAREA                           PIC X(01)
      *      OCCURS 1 TO 32767 TIMES DEPENDING ON EIBCALEN.

      *----------------------------------------------------------------*
      *                      PROCEDURE DIVISION
      *----------------------------------------------------------------*
       PROCEDURE DIVISION.
      *MAIN-PARA.
           CONTINUE.
      *    DISPLAY 'SPECTER-TRACE:MAIN-PARA'.

      *    SET ERR-FLG-OFF TO TRUE

      *    MOVE SPACES TO WS-MESSAGE
      *                   ERRMSGO OF COSGN0AO

      *    IF EIBCALEN = 0
      *        MOVE LOW-VALUES TO COSGN0AO
      *        MOVE -1       TO USERIDL OF COSGN0AI
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=SEND-SIGNON-SCREEN'.
      *        PERFORM SEND-SIGNON-SCREEN
      *    ELSE
      *        EVALUATE EIBAID
      *            WHEN DFHENTER
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=PROCESS-ENTER-KEY'.
      *                PERFORM PROCESS-ENTER-KEY
      *            WHEN DFHPF3
      *                MOVE CCDA-MSG-THANK-YOU        TO WS-MESSAGE
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=SEND-PLAIN-TEXT'.
      *                PERFORM SEND-PLAIN-TEXT
      *            WHEN OTHER
      *                MOVE 'Y'                       TO WS-ERR-FLG
      *                MOVE CCDA-MSG-INVALID-KEY      TO WS-MESSAGE
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=SEND-SIGNON-SCREEN'.
      *                PERFORM SEND-SIGNON-SCREEN
      *        END-EVALUATE
      *    END-IF.

      *    EXEC CICS RETURN
      *              TRANSID (WS-TRANID)
      *              COMMAREA (CARDDEMO-COMMAREA)
      *              LENGTH(LENGTH OF CARDDEMO-COMMAREA)
      *    END-EXEC.
      *    DISPLAY 'SPECTER-CICS:RETURN'
      *    GO TO SPECTER-EXIT-PARA.


      *----------------------------------------------------------------*
      *                      PROCESS-ENTER-KEY
      *----------------------------------------------------------------*
       PROCESS-ENTER-KEY.
           DISPLAY 'SPECTER-TRACE:PROCESS-ENTER-KEY'.
           CONTINUE.

      *    EXEC CICS RECEIVE
      *              MAP('COSGN0A')
      *              MAPSET('COSGN00')
      *              RESP(WS-RESP-CD)
      *              RESP2(WS-REAS-CD)
      *    END-EXEC.
      *    DISPLAY 'SPECTER-MOCK:CICS-RECEIVE'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ
      *    MOVE MOCK-ALPHA-STATUS(1:1) TO EIBAID
      *    MOVE MOCK-NUM-STATUS TO WS-RESP-CD
      *    MOVE 0 TO WS-REAS-CD.

      *    EVALUATE TRUE
      *        WHEN USERIDI OF COSGN0AI = SPACES OR LOW-VALUES
      *            MOVE 'Y'      TO WS-ERR-FLG
      *            MOVE 'Please enter User ID ...' TO WS-MESSAGE
      *            MOVE -1       TO USERIDL OF COSGN0AI
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=SEND-SIGNON-SCREEN'.
      *            PERFORM SEND-SIGNON-SCREEN
      *        WHEN PASSWDI OF COSGN0AI = SPACES OR LOW-VALUES
      *            MOVE 'Y'      TO WS-ERR-FLG
      *            MOVE 'Please enter Password ...' TO WS-MESSAGE
      *            MOVE -1       TO PASSWDL OF COSGN0AI
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=SEND-SIGNON-SCREEN'.
      *            PERFORM SEND-SIGNON-SCREEN
      *        WHEN OTHER
      *            CONTINUE
      *    END-EVALUATE.

      *    MOVE FUNCTION UPPER-CASE(USERIDI OF COSGN0AI) TO
      *                    WS-USER-ID
      *                    CDEMO-USER-ID
      *    MOVE FUNCTION UPPER-CASE(PASSWDI OF COSGN0AI) TO
      *                    WS-USER-PWD

      *    IF NOT ERR-FLG-ON
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=READ-USER-SEC-FILE'.
      *        PERFORM READ-USER-SEC-FILE
      *    END-IF.

      *----------------------------------------------------------------*
      *                      SEND-SIGNON-SCREEN
      *----------------------------------------------------------------*
       SEND-SIGNON-SCREEN.
           DISPLAY 'SPECTER-TRACE:SEND-SIGNON-SCREEN'.
           CONTINUE.

      *    DISPLAY 'SPECTER-CALL:FROM=SEND-SIGNON-SCREEN:TO=POPULATE-HEADER-INFO'.
      *    PERFORM POPULATE-HEADER-INFO

      *    MOVE WS-MESSAGE TO ERRMSGO OF COSGN0AO

      *    EXEC CICS SEND
      *              MAP('COSGN0A')
      *              MAPSET('COSGN00')
      *              FROM(COSGN0AO)
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
      *                      SEND-PLAIN-TEXT
      *----------------------------------------------------------------*
       SEND-PLAIN-TEXT.
           DISPLAY 'SPECTER-TRACE:SEND-PLAIN-TEXT'.

      *    EXEC CICS SEND TEXT
      *              FROM(WS-MESSAGE)
      *              LENGTH(LENGTH OF WS-MESSAGE)
      *              ERASE
      *              FREEKB
      *    END-EXEC.
      *    DISPLAY 'SPECTER-MOCK:CICS-SEND'
           READ MOCK-FILE INTO MOCK-RECORD
              AT END
                MOVE '00' TO MOCK-ALPHA-STATUS
                MOVE 0 TO MOCK-NUM-STATUS
           END-READ.

      *    EXEC CICS RETURN
      *    END-EXEC.
           DISPLAY 'SPECTER-CICS:RETURN'
           GO TO SPECTER-EXIT-PARA.

      *----------------------------------------------------------------*
      *                      POPULATE-HEADER-INFO
      *----------------------------------------------------------------*
       POPULATE-HEADER-INFO.
           DISPLAY 'SPECTER-TRACE:POPULATE-HEADER-INFO'.

           MOVE FUNCTION CURRENT-DATE  TO WS-CURDATE-DATA

      *    MOVE CCDA-TITLE01           TO TITLE01O OF COSGN0AO
      *    MOVE CCDA-TITLE02           TO TITLE02O OF COSGN0AO
      *    MOVE WS-TRANID              TO TRNNAMEO OF COSGN0AO
      *    MOVE WS-PGMNAME             TO PGMNAMEO OF COSGN0AO

           MOVE WS-CURDATE-MONTH       TO WS-CURDATE-MM
           MOVE WS-CURDATE-DAY         TO WS-CURDATE-DD
           MOVE WS-CURDATE-YEAR(3:2)   TO WS-CURDATE-YY

      *    MOVE WS-CURDATE-MM-DD-YY    TO CURDATEO OF COSGN0AO

           MOVE WS-CURTIME-HOURS       TO WS-CURTIME-HH
           MOVE WS-CURTIME-MINUTE      TO WS-CURTIME-MM
           MOVE WS-CURTIME-SECOND      TO WS-CURTIME-SS

      *    MOVE WS-CURTIME-HH-MM-SS    TO CURTIMEO OF COSGN0AO

      *    EXEC CICS ASSIGN
      *        APPLID(APPLIDO OF COSGN0AO)
      *    END-EXEC
           DISPLAY 'SPECTER-MOCK:CICS'
           READ MOCK-FILE INTO MOCK-RECORD
              AT END
                MOVE '00' TO MOCK-ALPHA-STATUS
                MOVE 0 TO MOCK-NUM-STATUS
           END-READ

      *    EXEC CICS ASSIGN
      *        SYSID(SYSIDO OF COSGN0AO)
      *    END-EXEC.
           DISPLAY 'SPECTER-MOCK:CICS'
           READ MOCK-FILE INTO MOCK-RECORD
              AT END
                MOVE '00' TO MOCK-ALPHA-STATUS
                MOVE 0 TO MOCK-NUM-STATUS
           END-READ.

      *----------------------------------------------------------------*
      *                      READ-USER-SEC-FILE
      *----------------------------------------------------------------*
       READ-USER-SEC-FILE.
           DISPLAY 'SPECTER-TRACE:READ-USER-SEC-FILE'.
           CONTINUE.

      *    EXEC CICS READ
      *         DATASET   (WS-USRSEC-FILE)
      *         INTO      (SEC-USER-DATA)
      *         LENGTH    (LENGTH OF SEC-USER-DATA)
      *         RIDFLD    (WS-USER-ID)
      *         KEYLENGTH (LENGTH OF WS-USER-ID)
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
      *            IF SEC-USR-PWD = WS-USER-PWD
      *                MOVE WS-TRANID    TO CDEMO-FROM-TRANID
      *                MOVE WS-PGMNAME   TO CDEMO-FROM-PROGRAM
      *                MOVE WS-USER-ID   TO CDEMO-USER-ID
      *                MOVE SEC-USR-TYPE TO CDEMO-USER-TYPE
      *                MOVE ZEROS        TO CDEMO-PGM-CONTEXT

      *                IF CDEMO-USRTYP-ADMIN
      *                     EXEC CICS XCTL
      *                       PROGRAM ('COADM01C')
      *                       COMMAREA(CARDDEMO-COMMAREA)
      *                     END-EXEC
      *    DISPLAY 'SPECTER-CICS:XCTL:'COADM01C''
      *    GO TO SPECTER-EXIT-PARA
      *                ELSE
      *                     EXEC CICS XCTL
      *                       PROGRAM ('COMEN01C')
      *                       COMMAREA(CARDDEMO-COMMAREA)
      *                     END-EXEC
      *    DISPLAY 'SPECTER-CICS:XCTL:'COMEN01C''
      *    GO TO SPECTER-EXIT-PARA
      *                END-IF
      *            ELSE
      *                MOVE 'Wrong Password. Try again ...' TO
      *                                                   WS-MESSAGE
      *                MOVE -1       TO PASSWDL OF COSGN0AI
      *    DISPLAY 'SPECTER-CALL:FROM=READ-USER-SEC-FILE:TO=SEND-SIGNON-SCREEN'.
      *                PERFORM SEND-SIGNON-SCREEN
      *            END-IF
      *        WHEN 13
      *            MOVE 'Y'      TO WS-ERR-FLG
      *            MOVE 'User not found. Try again ...' TO WS-MESSAGE
      *            MOVE -1       TO USERIDL OF COSGN0AI
      *    DISPLAY 'SPECTER-CALL:FROM=READ-USER-SEC-FILE:TO=SEND-SIGNON-SCREEN'.
      *            PERFORM SEND-SIGNON-SCREEN
      *        WHEN OTHER
      *            MOVE 'Y'      TO WS-ERR-FLG
      *            MOVE 'Unable to verify the User ...' TO WS-MESSAGE
      *            MOVE -1       TO USERIDL OF COSGN0AI
      *    DISPLAY 'SPECTER-CALL:FROM=READ-USER-SEC-FILE:TO=SEND-SIGNON-SCREEN'.
      *            PERFORM SEND-SIGNON-SCREEN
      *    END-EVALUATE.
      *
      * Ver: CardDemo_v1.0-15-g27d6c6f-68 Date: 2022-07-19 23:12:33 CDT
      *

      * SPECTER: exit paragraph for CICS RETURN/XCTL
       SPECTER-EXIT-PARA.
           CLOSE MOCK-FILE
           STOP RUN.
