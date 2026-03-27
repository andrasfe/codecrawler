      ******************************************************************        
      * Program     : COTRN00C.CBL
      * Application : CardDemo
      * Type        : CICS COBOL Program
      * Function    : List Transactions from TRANSACT file
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
       PROGRAM-ID. COTRN00C.
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
       01 YOU                            PIC X(256).
      * SPECTER PATCH: cobc-undefined fallback declarations
       01 INITIALIZE-TRAN-DATA           PIC X(256).
       01 POPULATE-TRAN-DATA             PIC X(256).
       01 PROCESS-ENTER-KEY              PIC X(256).
       01 PROCESS-PAGE-BACKWARD          PIC X(256).
       01 PROCESS-PAGE-FORWARD           PIC X(256).
       01 RESP                           PIC X(256).
       01 SEND-TRNLST-SCREEN             PIC X(256).
       01 SPECTER-CALL                   PIC X(256).
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
         05 WS-PGMNAME                 PIC X(08) VALUE 'COTRN00C'.
         05 WS-TRANID                  PIC X(04) VALUE 'CT00'.
         05 WS-MESSAGE                 PIC X(80) VALUE SPACES.
         05 WS-TRANSACT-FILE             PIC X(08) VALUE 'TRANSACT'.
         05 WS-ERR-FLG                 PIC X(01) VALUE 'N'.
           88 ERR-FLG-ON                         VALUE 'Y'.
           88 ERR-FLG-OFF                        VALUE 'N'.
         05 WS-TRANSACT-EOF            PIC X(01) VALUE 'N'.
           88 TRANSACT-EOF                       VALUE 'Y'.
           88 TRANSACT-NOT-EOF                   VALUE 'N'.
         05 WS-SEND-ERASE-FLG          PIC X(01) VALUE 'Y'.
           88 SEND-ERASE-YES                     VALUE 'Y'.
           88 SEND-ERASE-NO                      VALUE 'N'.

         05 WS-RESP-CD                 PIC S9(09) COMP VALUE ZEROS.
         05 WS-REAS-CD                 PIC S9(09) COMP VALUE ZEROS.
         05 WS-REC-COUNT               PIC S9(04) COMP VALUE ZEROS.
         05 WS-IDX                     PIC S9(04) COMP VALUE ZEROS.
         05 WS-PAGE-NUM                PIC S9(04) COMP VALUE ZEROS.

         05 WS-TRAN-AMT                PIC +99999999.99.
         05 WS-TRAN-DATE               PIC X(08) VALUE '00/00/00'.



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
          05 CDEMO-CT00-INFO.
             10 CDEMO-CT00-TRNID-FIRST     PIC X(16).
             10 CDEMO-CT00-TRNID-LAST      PIC X(16).
             10 CDEMO-CT00-PAGE-NUM        PIC 9(08).
             10 CDEMO-CT00-NEXT-PAGE-FLG   PIC X(01) VALUE 'N'.
                88 NEXT-PAGE-YES                     VALUE 'Y'.
                88 NEXT-PAGE-NO                      VALUE 'N'.
             10 CDEMO-CT00-TRN-SEL-FLG     PIC X(01).
             10 CDEMO-CT00-TRN-SELECTED    PIC X(16).

      * SPECTER: COPY COTRN00 (not found)

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

      * SPECTER: COPY CVTRA05Y inlined from CVTRA05Y.cpy
      *****************************************************************         
      *    Data-structure for TRANsaction record (RECLN = 350)                  
      *****************************************************************         
       01  TRAN-RECORD.                                                         
           05  TRAN-ID                                 PIC X(16).               
           05  TRAN-TYPE-CD                            PIC X(02).               
           05  TRAN-CAT-CD                             PIC 9(04).               
           05  TRAN-SOURCE                             PIC X(10).               
           05  TRAN-DESC                               PIC X(100).              
           05  TRAN-AMT                                PIC S9(09)V99.           
           05  TRAN-MERCHANT-ID                        PIC 9(09).               
           05  TRAN-MERCHANT-NAME                      PIC X(50).               
           05  TRAN-MERCHANT-CITY                      PIC X(50).               
           05  TRAN-MERCHANT-ZIP                       PIC X(10).               
           05  TRAN-CARD-NUM                           PIC X(16).               
           05  TRAN-ORIG-TS                            PIC X(26).               
           05  TRAN-PROC-TS                            PIC X(26).               
           05  FILLER                                  PIC X(20).               
       01  DFHCOMMAREA.
         05  LK-COMMAREA                           PIC X(01)
             OCCURS 1 TO 32767 TIMES DEPENDING ON EIBCALEN.
      *
      * Ver: CardDemo_v1.0-15-g27d6c6f-68 Date: 2022-07-19 23:16:01 CDT
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

      *    SET ERR-FLG-OFF TO TRUE
      *    SET TRANSACT-NOT-EOF TO TRUE
      *    SET NEXT-PAGE-NO TO TRUE
      *    SET SEND-ERASE-YES TO TRUE

      *    MOVE SPACES TO WS-MESSAGE
      *                   ERRMSGO OF COTRN0AO

      *    MOVE -1       TO TRNIDINL OF COTRN0AI

      *    IF EIBCALEN = 0
      *        MOVE 'COSGN00C' TO CDEMO-TO-PROGRAM
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=RETURN-TO-PREV-SCREEN'.
      *        PERFORM RETURN-TO-PREV-SCREEN
      *    ELSE
      *        MOVE DFHCOMMAREA(1:EIBCALEN) TO CARDDEMO-COMMAREA
      *        IF NOT CDEMO-PGM-REENTER
      *            SET CDEMO-PGM-REENTER    TO TRUE
      *            MOVE LOW-VALUES          TO COTRN0AO
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=PROCESS-ENTER-KEY'.
      *            PERFORM PROCESS-ENTER-KEY
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=SEND-TRNLST-SCREEN'.
      *            PERFORM SEND-TRNLST-SCREEN
      *        ELSE
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=RECEIVE-TRNLST-SCREEN'.
      *            PERFORM RECEIVE-TRNLST-SCREEN
      *            EVALUATE EIBAID
      *                WHEN DFHENTER
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=PROCESS-ENTER-KEY'.
      *                    PERFORM PROCESS-ENTER-KEY
      *                WHEN DFHPF3
      *                    MOVE 'COMEN01C' TO CDEMO-TO-PROGRAM
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=RETURN-TO-PREV-SCREEN'.
      *                    PERFORM RETURN-TO-PREV-SCREEN
      *                WHEN DFHPF7
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=PROCESS-PF7-KEY'.
      *                    PERFORM PROCESS-PF7-KEY
      *                WHEN DFHPF8
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=PROCESS-PF8-KEY'.
      *                    PERFORM PROCESS-PF8-KEY
      *                WHEN OTHER
      *                    MOVE 'Y'                       TO WS-ERR-FLG
      *                    MOVE -1       TO TRNIDINL OF COTRN0AI
      *                    MOVE CCDA-MSG-INVALID-KEY      TO WS-MESSAGE
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=SEND-TRNLST-SCREEN'.
      *                    PERFORM SEND-TRNLST-SCREEN
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
      *PROCESS-ENTER-KEY.
           CONTINUE.

      *    EVALUATE TRUE
      *        WHEN SEL0001I OF COTRN0AI NOT = SPACES AND LOW-VALUES
      *            MOVE SEL0001I OF COTRN0AI TO CDEMO-CT00-TRN-SEL-FLG
      *            MOVE TRNID01I OF COTRN0AI TO CDEMO-CT00-TRN-SELECTED
      *        WHEN SEL0002I OF COTRN0AI NOT = SPACES AND LOW-VALUES
      *            MOVE SEL0002I OF COTRN0AI TO CDEMO-CT00-TRN-SEL-FLG
      *            MOVE TRNID02I OF COTRN0AI TO CDEMO-CT00-TRN-SELECTED
      *        WHEN SEL0003I OF COTRN0AI NOT = SPACES AND LOW-VALUES
      *            MOVE SEL0003I OF COTRN0AI TO CDEMO-CT00-TRN-SEL-FLG
      *            MOVE TRNID03I OF COTRN0AI TO CDEMO-CT00-TRN-SELECTED
      *        WHEN SEL0004I OF COTRN0AI NOT = SPACES AND LOW-VALUES
      *            MOVE SEL0004I OF COTRN0AI TO CDEMO-CT00-TRN-SEL-FLG
      *            MOVE TRNID04I OF COTRN0AI TO CDEMO-CT00-TRN-SELECTED
      *        WHEN SEL0005I OF COTRN0AI NOT = SPACES AND LOW-VALUES
      *            MOVE SEL0005I OF COTRN0AI TO CDEMO-CT00-TRN-SEL-FLG
      *            MOVE TRNID05I OF COTRN0AI TO CDEMO-CT00-TRN-SELECTED
      *        WHEN SEL0006I OF COTRN0AI NOT = SPACES AND LOW-VALUES
      *            MOVE SEL0006I OF COTRN0AI TO CDEMO-CT00-TRN-SEL-FLG
      *            MOVE TRNID06I OF COTRN0AI TO CDEMO-CT00-TRN-SELECTED
      *        WHEN SEL0007I OF COTRN0AI NOT = SPACES AND LOW-VALUES
      *            MOVE SEL0007I OF COTRN0AI TO CDEMO-CT00-TRN-SEL-FLG
      *            MOVE TRNID07I OF COTRN0AI TO CDEMO-CT00-TRN-SELECTED
      *        WHEN SEL0008I OF COTRN0AI NOT = SPACES AND LOW-VALUES
      *            MOVE SEL0008I OF COTRN0AI TO CDEMO-CT00-TRN-SEL-FLG
      *            MOVE TRNID08I OF COTRN0AI TO CDEMO-CT00-TRN-SELECTED
      *        WHEN SEL0009I OF COTRN0AI NOT = SPACES AND LOW-VALUES
      *            MOVE SEL0009I OF COTRN0AI TO CDEMO-CT00-TRN-SEL-FLG
      *            MOVE TRNID09I OF COTRN0AI TO CDEMO-CT00-TRN-SELECTED
      *        WHEN SEL0010I OF COTRN0AI NOT = SPACES AND LOW-VALUES
      *            MOVE SEL0010I OF COTRN0AI TO CDEMO-CT00-TRN-SEL-FLG
      *            MOVE TRNID10I OF COTRN0AI TO CDEMO-CT00-TRN-SELECTED
      *        WHEN OTHER
      *            MOVE SPACES   TO CDEMO-CT00-TRN-SEL-FLG
      *            MOVE SPACES   TO CDEMO-CT00-TRN-SELECTED
      *    END-EVALUATE
      *    IF (CDEMO-CT00-TRN-SEL-FLG NOT = SPACES AND LOW-VALUES) AND
      *       (CDEMO-CT00-TRN-SELECTED NOT = SPACES AND LOW-VALUES)
      *        EVALUATE CDEMO-CT00-TRN-SEL-FLG
      *            WHEN 'S'
      *            WHEN 's'
      *                 MOVE 'COTRN01C'   TO CDEMO-TO-PROGRAM
      *                 MOVE WS-TRANID    TO CDEMO-FROM-TRANID
      *                 MOVE WS-PGMNAME   TO CDEMO-FROM-PROGRAM
      *                 MOVE 0        TO CDEMO-PGM-CONTEXT
      *                 EXEC CICS
      *                     XCTL PROGRAM(CDEMO-TO-PROGRAM)
      *                     COMMAREA(CARDDEMO-COMMAREA)
      *                 END-EXEC
      *    DISPLAY 'SPECTER-CICS:XCTL:CDEMO-TO-PROGRAM'
      *    GO TO SPECTER-EXIT-PARA
      *            WHEN OTHER
      *                SET TRANSACT-EOF TO TRUE
      *                MOVE
      *                'Invalid selection. Valid value is S' TO
      *                                WS-MESSAGE
      *                MOVE -1       TO TRNIDINL OF COTRN0AI
      *                PERFORM SEND-TRNLST-SCREEN
      *        END-EVALUATE
      *    END-IF

      *    IF TRNIDINI OF COTRN0AI = SPACES OR LOW-VALUES
      *        MOVE LOW-VALUES TO TRAN-ID
      *    ELSE
      *        IF TRNIDINI  OF COTRN0AI IS NUMERIC
      *            MOVE TRNIDINI  OF COTRN0AI    TO TRAN-ID
      *        ELSE
      *            MOVE 'Y'                       TO WS-ERR-FLG
      *            MOVE
      *            'Tran ID must be Numeric ...' TO
      *                            WS-MESSAGE
      *            MOVE -1                 TO TRNIDINL OF COTRN0AI
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=SEND-TRNLST-SCREEN'.
      *            PERFORM SEND-TRNLST-SCREEN
      *        END-IF
      *    END-IF

      *    MOVE -1       TO TRNIDINL OF COTRN0AI


      *    MOVE 0       TO CDEMO-CT00-PAGE-NUM
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=PROCESS-PAGE-FORWARD'.
      *    PERFORM PROCESS-PAGE-FORWARD

      *    IF NOT ERR-FLG-ON
      *        MOVE SPACE   TO TRNIDINO  OF COTRN0AO
      *    END-IF.

      *----------------------------------------------------------------*
      *                      PROCESS-PF7-KEY
      *----------------------------------------------------------------*
      *PROCESS-PF7-KEY.
      *    DISPLAY 'SPECTER-TRACE:PROCESS-PF7-KEY'.

      *    IF CDEMO-CT00-TRNID-FIRST = SPACES OR LOW-VALUES
      *        MOVE LOW-VALUES TO TRAN-ID
      *    ELSE
      *        MOVE CDEMO-CT00-TRNID-FIRST TO TRAN-ID
      *    END-IF

      *    SET NEXT-PAGE-YES TO TRUE
      *    MOVE -1       TO TRNIDINL OF COTRN0AI

      *    IF CDEMO-CT00-PAGE-NUM > 1
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PF7-KEY:TO=PROCESS-PAGE-BACKWARD'.
      *        PERFORM PROCESS-PAGE-BACKWARD
      *    ELSE
      *        MOVE 'You are already at the top of the page...' TO
      *                        WS-MESSAGE
      *        SET SEND-ERASE-NO TO TRUE
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PF7-KEY:TO=SEND-TRNLST-SCREEN'.
      *        PERFORM SEND-TRNLST-SCREEN
      *    END-IF.

      *----------------------------------------------------------------*
      *                      PROCESS-PF8-KEY
      *----------------------------------------------------------------*
       PROCESS-PF8-KEY.
           DISPLAY 'SPECTER-TRACE:PROCESS-PF8-KEY'.
           CONTINUE.

      *    IF CDEMO-CT00-TRNID-LAST = SPACES OR LOW-VALUES
      *        MOVE HIGH-VALUES TO TRAN-ID
      *    ELSE
      *        MOVE CDEMO-CT00-TRNID-LAST TO TRAN-ID
      *    END-IF

      *    MOVE -1       TO TRNIDINL OF COTRN0AI

      *    IF NEXT-PAGE-YES
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PF8-KEY:TO=PROCESS-PAGE-FORWARD'.
      *        PERFORM PROCESS-PAGE-FORWARD
      *    ELSE
      *        MOVE 'You are already at the bottom of the page...' TO
      *                        WS-MESSAGE
      *        SET SEND-ERASE-NO TO TRUE
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PF8-KEY:TO=SEND-TRNLST-SCREEN'.
      *        PERFORM SEND-TRNLST-SCREEN
      *    END-IF.

      *----------------------------------------------------------------*
      *                      PROCESS-PAGE-FORWARD
      *----------------------------------------------------------------*
      *PROCESS-PAGE-FORWARD.
           CONTINUE.

      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-FORWARD:TO=STARTBR-TRANSACT-FILE'.
      *    PERFORM STARTBR-TRANSACT-FILE

      *    IF NOT ERR-FLG-ON

      *        IF EIBAID NOT = DFHENTER AND DFHPF7 AND DFHPF3
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-FORWARD:TO=READNEXT-TRANSACT-FILE'.
      *            PERFORM READNEXT-TRANSACT-FILE
      *        END-IF

      *        IF TRANSACT-NOT-EOF AND ERR-FLG-OFF
      *           PERFORM VARYING WS-IDX FROM 1 BY 1 UNTIL WS-IDX > 10
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-FORWARD:TO=INITIALIZE-TRAN-DATA'.
      *               PERFORM INITIALIZE-TRAN-DATA
      *           END-PERFORM
      *        END-IF

      *        MOVE 1             TO  WS-IDX

      *        PERFORM UNTIL WS-IDX >= 11 OR TRANSACT-EOF OR ERR-FLG-ON
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-FORWARD:TO=READNEXT-TRANSACT-FILE'.
      *            PERFORM READNEXT-TRANSACT-FILE
      *            IF TRANSACT-NOT-EOF AND ERR-FLG-OFF
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-FORWARD:TO=POPULATE-TRAN-DATA'.
      *                PERFORM POPULATE-TRAN-DATA
      *                COMPUTE WS-IDX = WS-IDX + 1
      *            END-IF
      *        END-PERFORM

      *        IF TRANSACT-NOT-EOF AND ERR-FLG-OFF
      *            COMPUTE CDEMO-CT00-PAGE-NUM =
      *                    CDEMO-CT00-PAGE-NUM + 1
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-FORWARD:TO=READNEXT-TRANSACT-FILE'.
      *            PERFORM READNEXT-TRANSACT-FILE
      *            IF TRANSACT-NOT-EOF AND ERR-FLG-OFF
      *                SET NEXT-PAGE-YES TO TRUE
      *            ELSE
      *                SET NEXT-PAGE-NO TO TRUE
      *            END-IF
      *        ELSE
      *            SET NEXT-PAGE-NO TO TRUE
      *            IF WS-IDX > 1
      *                COMPUTE CDEMO-CT00-PAGE-NUM = CDEMO-CT00-PAGE-NUM
      *                 + 1
      *            END-IF
      *        END-IF

      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-FORWARD:TO=ENDBR-TRANSACT-FILE'.
      *        PERFORM ENDBR-TRANSACT-FILE

      *        MOVE CDEMO-CT00-PAGE-NUM TO PAGENUMI  OF COTRN0AI
      *        MOVE SPACE   TO TRNIDINO  OF COTRN0AO
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-FORWARD:TO=SEND-TRNLST-SCREEN'.
      *        PERFORM SEND-TRNLST-SCREEN

      *    END-IF.

      *----------------------------------------------------------------*
      *                      PROCESS-PAGE-BACKWARD
      *----------------------------------------------------------------*
      *PROCESS-PAGE-BACKWARD.
           CONTINUE.

      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-BACKWARD:TO=STARTBR-TRANSACT-FILE'.
      *    PERFORM STARTBR-TRANSACT-FILE

      *    IF NOT ERR-FLG-ON

      *        IF EIBAID NOT = DFHENTER AND DFHPF8
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-BACKWARD:TO=READPREV-TRANSACT-FILE'.
      *            PERFORM READPREV-TRANSACT-FILE
      *        END-IF

      *        IF TRANSACT-NOT-EOF AND ERR-FLG-OFF
      *           PERFORM VARYING WS-IDX FROM 1 BY 1 UNTIL WS-IDX > 10
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-BACKWARD:TO=INITIALIZE-TRAN-DATA'.
      *              PERFORM INITIALIZE-TRAN-DATA
      *           END-PERFORM
      *        END-IF

      *        MOVE 10          TO  WS-IDX

      *        PERFORM UNTIL WS-IDX <= 0 OR TRANSACT-EOF OR ERR-FLG-ON
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-BACKWARD:TO=READPREV-TRANSACT-FILE'.
      *            PERFORM READPREV-TRANSACT-FILE
      *            IF TRANSACT-NOT-EOF AND ERR-FLG-OFF
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-BACKWARD:TO=POPULATE-TRAN-DATA'.
      *                PERFORM POPULATE-TRAN-DATA
      *                COMPUTE WS-IDX = WS-IDX - 1
      *            END-IF
      *        END-PERFORM

      *        IF TRANSACT-NOT-EOF AND ERR-FLG-OFF
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-BACKWARD:TO=READPREV-TRANSACT-FILE'.
      *           PERFORM READPREV-TRANSACT-FILE
      *           IF NEXT-PAGE-YES
      *              IF TRANSACT-NOT-EOF AND ERR-FLG-OFF AND
      *                 CDEMO-CT00-PAGE-NUM > 1
      *                 SUBTRACT 1 FROM CDEMO-CT00-PAGE-NUM
      *              ELSE
      *                 MOVE 1 TO CDEMO-CT00-PAGE-NUM
      *              END-IF
      *           END-IF
      *        END-IF

      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-BACKWARD:TO=ENDBR-TRANSACT-FILE'.
      *        PERFORM ENDBR-TRANSACT-FILE

      *        MOVE CDEMO-CT00-PAGE-NUM TO PAGENUMI  OF COTRN0AI
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-PAGE-BACKWARD:TO=SEND-TRNLST-SCREEN'.
      *        PERFORM SEND-TRNLST-SCREEN

      *    END-IF.

      *----------------------------------------------------------------*
      *                      POPULATE-TRAN-DATA
      *----------------------------------------------------------------*
      *POPULATE-TRAN-DATA.
           CONTINUE.

      *    MOVE TRAN-AMT                  TO WS-TRAN-AMT
      *    MOVE TRAN-ORIG-TS              TO WS-TIMESTAMP
      *    MOVE WS-TIMESTAMP-DT-YYYY(3:2) TO WS-CURDATE-YY
      *    MOVE WS-TIMESTAMP-DT-MM        TO WS-CURDATE-MM
      *    MOVE WS-TIMESTAMP-DT-DD        TO WS-CURDATE-DD
      *    MOVE WS-CURDATE-MM-DD-YY       TO WS-TRAN-DATE

      *    EVALUATE WS-IDX
      *        WHEN 1
      *            MOVE TRAN-ID    TO TRNID01I OF COTRN0AI
      *                                  CDEMO-CT00-TRNID-FIRST
      *            MOVE WS-TRAN-DATE TO TDATE01I OF COTRN0AI
      *            MOVE TRAN-DESC TO TDESC01I OF COTRN0AI
      *            MOVE WS-TRAN-AMT  TO TAMT001I OF COTRN0AI
      *        WHEN 2
      *            MOVE TRAN-ID    TO TRNID02I OF COTRN0AI
      *            MOVE WS-TRAN-DATE TO TDATE02I OF COTRN0AI
      *            MOVE TRAN-DESC TO TDESC02I OF COTRN0AI
      *            MOVE WS-TRAN-AMT  TO TAMT002I OF COTRN0AI
      *        WHEN 3
      *            MOVE TRAN-ID    TO TRNID03I OF COTRN0AI
      *            MOVE WS-TRAN-DATE TO TDATE03I OF COTRN0AI
      *            MOVE TRAN-DESC TO TDESC03I OF COTRN0AI
      *            MOVE WS-TRAN-AMT  TO TAMT003I OF COTRN0AI
      *        WHEN 4
      *            MOVE TRAN-ID    TO TRNID04I OF COTRN0AI
      *            MOVE WS-TRAN-DATE TO TDATE04I OF COTRN0AI
      *            MOVE TRAN-DESC TO TDESC04I OF COTRN0AI
      *            MOVE WS-TRAN-AMT  TO TAMT004I OF COTRN0AI
      *        WHEN 5
      *            MOVE TRAN-ID    TO TRNID05I OF COTRN0AI
      *            MOVE WS-TRAN-DATE TO TDATE05I OF COTRN0AI
      *            MOVE TRAN-DESC TO TDESC05I OF COTRN0AI
      *            MOVE WS-TRAN-AMT  TO TAMT005I OF COTRN0AI
      *        WHEN 6
      *            MOVE TRAN-ID    TO TRNID06I OF COTRN0AI
      *            MOVE WS-TRAN-DATE TO TDATE06I OF COTRN0AI
      *            MOVE TRAN-DESC TO TDESC06I OF COTRN0AI
      *            MOVE WS-TRAN-AMT  TO TAMT006I OF COTRN0AI
      *        WHEN 7
      *            MOVE TRAN-ID    TO TRNID07I OF COTRN0AI
      *            MOVE WS-TRAN-DATE TO TDATE07I OF COTRN0AI
      *            MOVE TRAN-DESC TO TDESC07I OF COTRN0AI
      *            MOVE WS-TRAN-AMT  TO TAMT007I OF COTRN0AI
      *        WHEN 8
      *            MOVE TRAN-ID    TO TRNID08I OF COTRN0AI
      *            MOVE WS-TRAN-DATE TO TDATE08I OF COTRN0AI
      *            MOVE TRAN-DESC TO TDESC08I OF COTRN0AI
      *            MOVE WS-TRAN-AMT  TO TAMT008I OF COTRN0AI
      *        WHEN 9
      *            MOVE TRAN-ID    TO TRNID09I OF COTRN0AI
      *            MOVE WS-TRAN-DATE TO TDATE09I OF COTRN0AI
      *            MOVE TRAN-DESC TO TDESC09I OF COTRN0AI
      *            MOVE WS-TRAN-AMT  TO TAMT009I OF COTRN0AI
      *        WHEN 10
      *            MOVE TRAN-ID    TO TRNID10I OF COTRN0AI
      *                                  CDEMO-CT00-TRNID-LAST
      *            MOVE WS-TRAN-DATE TO TDATE10I OF COTRN0AI
      *            MOVE TRAN-DESC TO TDESC10I OF COTRN0AI
      *            MOVE WS-TRAN-AMT  TO TAMT010I OF COTRN0AI
      *        WHEN OTHER
      *            CONTINUE
      *    END-EVALUATE.

      *----------------------------------------------------------------*
      *                      INITIALIZE-TRAN-DATA
      *----------------------------------------------------------------*
      *INITIALIZE-TRAN-DATA.
           CONTINUE.

      *    EVALUATE WS-IDX
      *        WHEN 1
      *            MOVE SPACES TO TRNID01I OF COTRN0AI
      *            MOVE SPACES TO TDATE01I OF COTRN0AI
      *            MOVE SPACES TO TDESC01I OF COTRN0AI
      *            MOVE SPACES TO TAMT001I OF COTRN0AI
      *        WHEN 2
      *            MOVE SPACES TO TRNID02I OF COTRN0AI
      *            MOVE SPACES TO TDATE02I OF COTRN0AI
      *            MOVE SPACES TO TDESC02I OF COTRN0AI
      *            MOVE SPACES TO TAMT002I OF COTRN0AI
      *        WHEN 3
      *            MOVE SPACES TO TRNID03I OF COTRN0AI
      *            MOVE SPACES TO TDATE03I OF COTRN0AI
      *            MOVE SPACES TO TDESC03I OF COTRN0AI
      *            MOVE SPACES TO TAMT003I OF COTRN0AI
      *        WHEN 4
      *            MOVE SPACES TO TRNID04I OF COTRN0AI
      *            MOVE SPACES TO TDATE04I OF COTRN0AI
      *            MOVE SPACES TO TDESC04I OF COTRN0AI
      *            MOVE SPACES TO TAMT004I OF COTRN0AI
      *        WHEN 5
      *            MOVE SPACES TO TRNID05I OF COTRN0AI
      *            MOVE SPACES TO TDATE05I OF COTRN0AI
      *            MOVE SPACES TO TDESC05I OF COTRN0AI
      *            MOVE SPACES TO TAMT005I OF COTRN0AI
      *        WHEN 6
      *            MOVE SPACES TO TRNID06I OF COTRN0AI
      *            MOVE SPACES TO TDATE06I OF COTRN0AI
      *            MOVE SPACES TO TDESC06I OF COTRN0AI
      *            MOVE SPACES TO TAMT006I OF COTRN0AI
      *        WHEN 7
      *            MOVE SPACES TO TRNID07I OF COTRN0AI
      *            MOVE SPACES TO TDATE07I OF COTRN0AI
      *            MOVE SPACES TO TDESC07I OF COTRN0AI
      *            MOVE SPACES TO TAMT007I OF COTRN0AI
      *        WHEN 8
      *            MOVE SPACES TO TRNID08I OF COTRN0AI
      *            MOVE SPACES TO TDATE08I OF COTRN0AI
      *            MOVE SPACES TO TDESC08I OF COTRN0AI
      *            MOVE SPACES TO TAMT008I OF COTRN0AI
      *        WHEN 9
      *            MOVE SPACES TO TRNID09I OF COTRN0AI
      *            MOVE SPACES TO TDATE09I OF COTRN0AI
      *            MOVE SPACES TO TDESC09I OF COTRN0AI
      *            MOVE SPACES TO TAMT009I OF COTRN0AI
      *        WHEN 10
      *            MOVE SPACES TO TRNID10I OF COTRN0AI
      *            MOVE SPACES TO TDATE10I OF COTRN0AI
      *            MOVE SPACES TO TDESC10I OF COTRN0AI
      *            MOVE SPACES TO TAMT010I OF COTRN0AI
      *        WHEN OTHER
      *            CONTINUE
      *    END-EVALUATE.

      *----------------------------------------------------------------*
      *                      RETURN-TO-PREV-SCREEN
      *----------------------------------------------------------------*
       RETURN-TO-PREV-SCREEN.
           DISPLAY 'SPECTER-TRACE:RETURN-TO-PREV-SCREEN'.

           IF CDEMO-TO-PROGRAM = LOW-VALUES OR SPACES
               MOVE 'COSGN00C' TO CDEMO-TO-PROGRAM
           END-IF
           MOVE WS-TRANID    TO CDEMO-FROM-TRANID
           MOVE WS-PGMNAME   TO CDEMO-FROM-PROGRAM
           MOVE ZEROS        TO CDEMO-PGM-CONTEXT
      *    EXEC CICS
      *        XCTL PROGRAM(CDEMO-TO-PROGRAM)
      *        COMMAREA(CARDDEMO-COMMAREA)
      *    END-EXEC.
           DISPLAY 'SPECTER-CICS:XCTL:CDEMO-TO-PROGRAM'
           GO TO SPECTER-EXIT-PARA.


      *----------------------------------------------------------------*
      *                      SEND-TRNLST-SCREEN
      *----------------------------------------------------------------*
      *SEND-TRNLST-SCREEN.
           CONTINUE.

      *    DISPLAY 'SPECTER-CALL:FROM=SEND-TRNLST-SCREEN:TO=POPULATE-HEADER-INFO'.
      *    PERFORM POPULATE-HEADER-INFO

      *    MOVE WS-MESSAGE TO ERRMSGO OF COTRN0AO

      *    IF SEND-ERASE-YES
      *        EXEC CICS SEND
      *                  MAP('COTRN0A')
      *                  MAPSET('COTRN00')
      *                  FROM(COTRN0AO)
      *                  ERASE
      *                  CURSOR
      *        END-EXEC
      *    DISPLAY 'SPECTER-MOCK:CICS-SEND'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ
      *    ELSE
      *        EXEC CICS SEND
      *                  MAP('COTRN0A')
      *                  MAPSET('COTRN00')
      *                  FROM(COTRN0AO)
      *                  ERASE
      *                  CURSOR
      *        END-EXEC
      *    DISPLAY 'SPECTER-MOCK:CICS-SEND'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ
      *    END-IF.

      *----------------------------------------------------------------*
      *                      RECEIVE-TRNLST-SCREEN
      *----------------------------------------------------------------*
       RECEIVE-TRNLST-SCREEN.
           DISPLAY 'SPECTER-TRACE:RECEIVE-TRNLST-SCREEN'.

      *    EXEC CICS RECEIVE
      *              MAP('COTRN0A')
      *              MAPSET('COTRN00')
      *              INTO(COTRN0AI)
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

      *    MOVE CCDA-TITLE01           TO TITLE01O OF COTRN0AO
      *    MOVE CCDA-TITLE02           TO TITLE02O OF COTRN0AO
      *    MOVE WS-TRANID              TO TRNNAMEO OF COTRN0AO
      *    MOVE WS-PGMNAME             TO PGMNAMEO OF COTRN0AO

      *    MOVE WS-CURDATE-MONTH       TO WS-CURDATE-MM
      *    MOVE WS-CURDATE-DAY         TO WS-CURDATE-DD
      *    MOVE WS-CURDATE-YEAR(3:2)   TO WS-CURDATE-YY

      *    MOVE WS-CURDATE-MM-DD-YY    TO CURDATEO OF COTRN0AO

      *    MOVE WS-CURTIME-HOURS       TO WS-CURTIME-HH
      *    MOVE WS-CURTIME-MINUTE      TO WS-CURTIME-MM
      *    MOVE WS-CURTIME-SECOND      TO WS-CURTIME-SS

      *    MOVE WS-CURTIME-HH-MM-SS    TO CURTIMEO OF COTRN0AO.

      *----------------------------------------------------------------*
      *                      STARTBR-TRANSACT-FILE
      *----------------------------------------------------------------*
      *S-S-S-S-S-S-S-S-S-S-S-STARTBR-.           
           CONTINUE.

      *    EXEC CICS STARTBR
      *         DATASET   (WS-TRANSACT-FILE)
      *         RIDFLD    (TRAN-ID)
      *         KEYLENGTH (LENGTH OF TRAN-ID)
      *         GTEQ
      *         RESP      (WS-RESP-CD)
      *         RESP2     (WS-REAS-CD)
      *    END-EXEC.
      *    DISPLAY 'SPECTER-MOCK:CICS-STARTBR'
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
      *        WHEN 13
      *            CONTINUE
      *            SET TRANSACT-EOF TO TRUE
      *            MOVE 'You are at the top of the page...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO TRNIDINL OF COTRN0AI
      *    DISPLAY 'SPECTER-CALL:FROM=STARTBR-TRANSACT-FILE:TO=SEND-TRNLST-SCREEN'.
      *            PERFORM SEND-TRNLST-SCREEN
      *        WHEN OTHER
      *            DISPLAY 'RESP:' WS-RESP-CD 'REAS:' WS-REAS-CD
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Unable to lookup transaction...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO TRNIDINL OF COTRN0AI
      *    DISPLAY 'SPECTER-CALL:FROM=STARTBR-TRANSACT-FILE:TO=SEND-TRNLST-SCREEN'.
      *            PERFORM SEND-TRNLST-SCREEN
      *    END-EVALUATE.

      *----------------------------------------------------------------*
      *                      READNEXT-TRANSACT-FILE
      *----------------------------------------------------------------*
       READNEXT-TRANSACT-FILE.
           DISPLAY 'SPECTER-TRACE:READNEXT-TRANSACT-FILE'.
           CONTINUE.

      *    EXEC CICS READNEXT
      *         DATASET   (WS-TRANSACT-FILE)
      *         INTO      (TRAN-RECORD)
      *         LENGTH    (LENGTH OF TRAN-RECORD)
      *         RIDFLD    (TRAN-ID)
      *         KEYLENGTH (LENGTH OF TRAN-ID)
      *         RESP      (WS-RESP-CD)
      *         RESP2     (WS-REAS-CD)
      *    END-EXEC.
      *    DISPLAY 'SPECTER-MOCK:CICS-READNEXT'
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
      *        WHEN 20
      *            CONTINUE
      *            SET TRANSACT-EOF TO TRUE
      *            MOVE 'You have reached the bottom of the page...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO TRNIDINL OF COTRN0AI
      *    DISPLAY 'SPECTER-CALL:FROM=READNEXT-TRANSACT-FILE:TO=SEND-TRNLST-SCREEN'.
      *            PERFORM SEND-TRNLST-SCREEN
      *        WHEN OTHER
      *            DISPLAY 'RESP:' WS-RESP-CD 'REAS:' WS-REAS-CD
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Unable to lookup transaction...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO TRNIDINL OF COTRN0AI
      *    DISPLAY 'SPECTER-CALL:FROM=READNEXT-TRANSACT-FILE:TO=SEND-TRNLST-SCREEN'.
      *            PERFORM SEND-TRNLST-SCREEN
      *    END-EVALUATE.

      *----------------------------------------------------------------*
      *                      READPREV-TRANSACT-FILE
      *----------------------------------------------------------------*
       READPREV-TRANSACT-FILE.
           DISPLAY 'SPECTER-TRACE:READPREV-TRANSACT-FILE'.
           CONTINUE.

      *    EXEC CICS READPREV
      *         DATASET   (WS-TRANSACT-FILE)
      *         INTO      (TRAN-RECORD)
      *         LENGTH    (LENGTH OF TRAN-RECORD)
      *         RIDFLD    (TRAN-ID)
      *         KEYLENGTH (LENGTH OF TRAN-ID)
      *         RESP      (WS-RESP-CD)
      *         RESP2     (WS-REAS-CD)
      *    END-EXEC.
      *    DISPLAY 'SPECTER-MOCK:CICS-READPREV'
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
      *        WHEN 20
      *            CONTINUE
      *            SET TRANSACT-EOF TO TRUE
      *            MOVE 'You have reached the top of the page...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO TRNIDINL OF COTRN0AI
      *    DISPLAY 'SPECTER-CALL:FROM=READPREV-TRANSACT-FILE:TO=SEND-TRNLST-SCREEN'.
      *            PERFORM SEND-TRNLST-SCREEN
      *        WHEN OTHER
      *            DISPLAY 'RESP:' WS-RESP-CD 'REAS:' WS-REAS-CD
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Unable to lookup transaction...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO TRNIDINL OF COTRN0AI
      *    DISPLAY 'SPECTER-CALL:FROM=READPREV-TRANSACT-FILE:TO=SEND-TRNLST-SCREEN'.
      *            PERFORM SEND-TRNLST-SCREEN
      *    END-EVALUATE.

      *----------------------------------------------------------------*
      *                      ENDBR-TRANSACT-FILE
      *----------------------------------------------------------------*
       ENDBR-TRANSACT-FILE.
           DISPLAY 'SPECTER-TRACE:ENDBR-TRANSACT-FILE'.

      *    EXEC CICS ENDBR
      *         DATASET   (WS-TRANSACT-FILE)
      *    END-EXEC.
           DISPLAY 'SPECTER-MOCK:CICS-ENDBR'
           READ MOCK-FILE INTO MOCK-RECORD
              AT END
                MOVE '00' TO MOCK-ALPHA-STATUS
                MOVE 0 TO MOCK-NUM-STATUS
           END-READ.
      *
      * Ver: CardDemo_v1.0-15-g27d6c6f-68 Date: 2022-07-19 23:12:34 CDT
      *

      * SPECTER: exit paragraph for CICS RETURN/XCTL

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.

      * SPECTER PATCH: cobc-undefined paragraph stubs.
       S-S-S-S-S-S-S-S-S-S-S-S-STARTB. 
           DISPLAY 'SPECTER-TRACE:S-S-S-S-S-S-S-S-S-S-S-S-STARTB'.
           EXIT.
       SPECTER-EXIT-PARA.
           CLOSE MOCK-FILE
           STOP RUN.
