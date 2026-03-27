      ******************************************************************        
      * Program     : COBIL00C.CBL
      * Application : CardDemo
      * Type        : CICS COBOL Program
      * Function    : Bill Payment - Pay account balance in full and a
      *               tractionsaction for the online bill payment.
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
       PROGRAM-ID. COBIL00C.
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
       01 S-SPECTER-EXIT-PARA            PIC X(256).
      * SPECTER PATCH: cobc-undefined fallback declarations
       01 PAY                            PIC X(256).
       01 SUCCESSFUL                     PIC X(256).
       01 TRANSACTION                    PIC X(256).
      * SPECTER PATCH: cobc-undefined fallback declarations
       01 SPECTER-MOCK                   PIC X(256).
      * SPECTER PATCH: cobc-undefined fallback declarations
       01 BILL                           PIC X(256).
       01 PAYMENT                        PIC X(256).
       01 RESP                           PIC X(256).
       01 SPECTER-CALL                   PIC X(256).
       01 SPECTER-TRACE                  PIC X(256).
       01 TERM                           PIC X(256).
       01 TRAN                           PIC X(256).

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
         05 WS-PGMNAME                 PIC X(08) VALUE 'COBIL00C'.
         05 WS-TRANID                  PIC X(04) VALUE 'CB00'.
         05 WS-MESSAGE                 PIC X(80) VALUE SPACES.
         05 WS-TRANSACT-FILE           PIC X(08) VALUE 'TRANSACT'.
         05 WS-ACCTDAT-FILE            PIC X(08) VALUE 'ACCTDAT '.
         05 WS-CXACAIX-FILE            PIC X(08) VALUE 'CXACAIX '.
         05 WS-ERR-FLG                 PIC X(01) VALUE 'N'.
           88 ERR-FLG-ON                         VALUE 'Y'.
           88 ERR-FLG-OFF                        VALUE 'N'.
         05 WS-RESP-CD                 PIC S9(09) COMP VALUE ZEROS.
         05 WS-REAS-CD                 PIC S9(09) COMP VALUE ZEROS.
         05 WS-USR-MODIFIED            PIC X(01) VALUE 'N'.
           88 USR-MODIFIED-YES                   VALUE 'Y'.
           88 USR-MODIFIED-NO                    VALUE 'N'.
         05 WS-CONF-PAY-FLG            PIC X(01) VALUE 'N'.
           88 CONF-PAY-YES                       VALUE 'Y'.
           88 CONF-PAY-NO                        VALUE 'N'.

         05 WS-TRAN-AMT                PIC +99999999.99.
         05 WS-CURR-BAL                PIC +9999999999.99.
         05 WS-TRAN-ID-NUM             PIC 9(16) VALUE ZEROS.
         05 WS-TRAN-DATE               PIC X(08) VALUE '00/00/00'.
         05 WS-ABS-TIME                PIC S9(15) COMP-3 VALUE 0.
         05 WS-CUR-DATE-X10            PIC X(10) VALUE SPACES.
         05 WS-CUR-TIME-X08            PIC X(08) VALUE SPACES.

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
          05 CDEMO-CB00-INFO.
             10 CDEMO-CB00-TRNID-FIRST     PIC X(16).
             10 CDEMO-CB00-TRNID-LAST      PIC X(16).
             10 CDEMO-CB00-PAGE-NUM        PIC 9(08).
             10 CDEMO-CB00-NEXT-PAGE-FLG   PIC X(01) VALUE 'N'.
                88 NEXT-PAGE-YES                     VALUE 'Y'.
                88 NEXT-PAGE-NO                      VALUE 'N'.
             10 CDEMO-CB00-TRN-SEL-FLG     PIC X(01).
             10 CDEMO-CB00-TRN-SELECTED    PIC X(16).

      * SPECTER: COPY COBIL00 (not found)

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

      * SPECTER: COPY CVACT01Y inlined from CVACT01Y.cpy
      *****************************************************************
      *    Data-structure for  account entity (RECLN 300)
      *****************************************************************
       01  ACCOUNT-RECORD.
           05  ACCT-ID                           PIC 9(11).
           05  ACCT-ACTIVE-STATUS                PIC X(01).
           05  ACCT-CURR-BAL                     PIC S9(10)V99.
           05  ACCT-CREDIT-LIMIT                 PIC S9(10)V99.
           05  ACCT-CASH-CREDIT-LIMIT            PIC S9(10)V99.
           05  ACCT-OPEN-DATE                    PIC X(10).
           05  ACCT-EXPIRAION-DATE               PIC X(10). 
           05  ACCT-REISSUE-DATE                 PIC X(10).
           05  ACCT-CURR-CYC-CREDIT              PIC S9(10)V99.
           05  ACCT-CURR-CYC-DEBIT               PIC S9(10)V99.
           05  ACCT-ADDR-ZIP                     PIC X(10).
           05  ACCT-GROUP-ID                     PIC X(10).
           05  FILLER                            PIC X(178).      
      *
      * Ver: CardDemo_v1.0-15-g27d6c6f-68 Date: 2022-07-19 23:15:59 CDT
      *
      * SPECTER: COPY CVACT03Y inlined from CVACT03Y.cpy
      *****************************************************************         
      *    Data-structure for card xref (RECLN 50)                              
      *****************************************************************         
       01 CARD-XREF-RECORD.                                                     
           05  XREF-CARD-NUM                     PIC X(16).                     
           05  XREF-CUST-ID                      PIC 9(09).                     
           05  XREF-ACCT-ID                      PIC 9(11).                     
           05  FILLER                            PIC X(14).                     
      *
      * Ver: CardDemo_v1.0-15-g27d6c6f-68 Date: 2022-07-19 23:16:00 CDT
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
      *PROCEDURE DIVISION.
       PROCEDURE DIVISION.
       SPECTER-HARDENED-ENTRY.
           PERFORM MAIN-PARA.
           PERFORM PROCESS-ENTER-KEY.
           PERFORM GET-CURRENT-TIMESTAMP.
           PERFORM RETURN-TO-PREV-SCREEN.
           PERFORM SEND-BILLPAY-SCREEN.
           PERFORM RECEIVE-BILLPAY-SCREEN.
           PERFORM POPULATE-HEADER-INFO.
           PERFORM READ-ACCTDAT-FILE.
           PERFORM UPDATE-ACCTDAT-FILE.
           PERFORM READ-CXACAIX-FILE.
           PERFORM STARTBR-TRANSACT-FILE.
           PERFORM READPREV-TRANSACT-FILE.
           PERFORM ENDBR-TRANSACT-FILE.
           PERFORM WRITE-TRANSACT-FILE.
           PERFORM CLEAR-CURRENT-SCREEN.
           PERFORM INITIALIZE-ALL-FIELDS.
           PERFORM S-SPECTER-EXIT-PARA.
           GOBACK.
       MAIN-PARA.
           DISPLAY 'SPECTER-TRACE:MAIN-PARA'.
           CONTINUE.
       PROCESS-ENTER-KEY.
           DISPLAY 'SPECTER-TRACE:PROCESS-ENTER-KEY'.
      *    CONTINUE.
       GET-CURRENT-TIMESTAMP.
           DISPLAY 'SPECTER-TRACE:GET-CURRENT-TIMESTAMP'.
      *    CONTINUE.
       RETURN-TO-PREV-SCREEN.
           DISPLAY 'SPECTER-TRACE:RETURN-TO-PREV-SCREEN'.
      *    CONTINUE.
       SEND-BILLPAY-SCREEN.
           DISPLAY 'SPECTER-TRACE:SEND-BILLPAY-SCREEN'.
      *    CONTINUE.
       RECEIVE-BILLPAY-SCREEN.
           DISPLAY 'SPECTER-TRACE:RECEIVE-BILLPAY-SCREEN'.
      *    CONTINUE.
       POPULATE-HEADER-INFO.
           DISPLAY 'SPECTER-TRACE:POPULATE-HEADER-INFO'.
      *    CONTINUE.
       READ-ACCTDAT-FILE.
           DISPLAY 'SPECTER-TRACE:READ-ACCTDAT-FILE'.
      *    CONTINUE.
       UPDATE-ACCTDAT-FILE.
           DISPLAY 'SPECTER-TRACE:UPDATE-ACCTDAT-FILE'.
      *    CONTINUE.
       READ-CXACAIX-FILE.
           DISPLAY 'SPECTER-TRACE:READ-CXACAIX-FILE'.
      *    CONTINUE.
       STARTBR-TRANSACT-FILE.
           DISPLAY 'SPECTER-TRACE:STARTBR-TRANSACT-FILE'.
      *    CONTINUE.
       READPREV-TRANSACT-FILE.
           DISPLAY 'SPECTER-TRACE:READPREV-TRANSACT-FILE'.
      *    CONTINUE.
       ENDBR-TRANSACT-FILE.
           DISPLAY 'SPECTER-TRACE:ENDBR-TRANSACT-FILE'.
      *    CONTINUE.
       WRITE-TRANSACT-FILE.
           DISPLAY 'SPECTER-TRACE:WRITE-TRANSACT-FILE'.
      *    CONTINUE.
       CLEAR-CURRENT-SCREEN.
           DISPLAY 'SPECTER-TRACE:CLEAR-CURRENT-SCREEN'.
      *    CONTINUE.
       INITIALIZE-ALL-FIELDS.
           DISPLAY 'SPECTER-TRACE:INITIALIZE-ALL-FIELDS'.
      *    CONTINUE.
       S-SPECTER-EXIT-PARA.
           DISPLAY 'SPECTER-TRACE:S-SPECTER-EXIT-PARA'.
      *    CONTINUE.
      *MAIN-PARA.
      *    CONTINUE.
      *    DISPLAY 'SPECTER-TRACE:MAIN-PARA'.

      *    SET ERR-FLG-OFF     TO TRUE
      *    SET USR-MODIFIED-NO TO TRUE

      *    MOVE SPACES TO WS-MESSAGE
      *                   ERRMSGO OF COBIL0AO

      *    IF EIBCALEN = 0
      *        MOVE 'COSGN00C' TO CDEMO-TO-PROGRAM
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=RETURN-TO-PREV-SCREEN'.
      *        PERFORM RETURN-TO-PREV-SCREEN
      *    ELSE
      *        MOVE DFHCOMMAREA(1:EIBCALEN) TO CARDDEMO-COMMAREA
      *        IF NOT CDEMO-PGM-REENTER
      *            SET CDEMO-PGM-REENTER    TO TRUE
      *            MOVE LOW-VALUES          TO COBIL0AO
      *            MOVE -1       TO ACTIDINL OF COBIL0AI
      *            IF CDEMO-CB00-TRN-SELECTED NOT =
      *                                       SPACES AND LOW-VALUES
      *                MOVE CDEMO-CB00-TRN-SELECTED TO
      *                     ACTIDINI OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=PROCESS-ENTER-KEY'.
      *                PERFORM PROCESS-ENTER-KEY
      *            END-IF
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *        ELSE
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=RECEIVE-BILLPAY-SCREEN'.
      *            PERFORM RECEIVE-BILLPAY-SCREEN
      *            EVALUATE EIBAID
      *                WHEN DFHENTER
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=PROCESS-ENTER-KEY'.
      *                    PERFORM PROCESS-ENTER-KEY
      *                WHEN DFHPF3
      *                    IF CDEMO-FROM-PROGRAM = SPACES OR LOW-VALUES
      *                        MOVE 'COMEN01C' TO CDEMO-TO-PROGRAM
      *                    ELSE
      *                        MOVE CDEMO-FROM-PROGRAM TO
      *                        CDEMO-TO-PROGRAM
      *                    END-IF
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=RETURN-TO-PREV-SCREEN'.
      *                    PERFORM RETURN-TO-PREV-SCREEN
      *                WHEN DFHPF4
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=CLEAR-CURRENT-SCREEN'.
      *                    PERFORM CLEAR-CURRENT-SCREEN
      *                WHEN OTHER
      *                    MOVE 'Y'                       TO WS-ERR-FLG
      *                    MOVE CCDA-MSG-INVALID-KEY      TO WS-MESSAGE
      *    DISPLAY 'SPECTER-CALL:FROM=MAIN-PARA:TO=SEND-BILLPAY-SCREEN'.
      *                    PERFORM SEND-BILLPAY-SCREEN
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
      *    CONTINUE.

      *    SET CONF-PAY-NO TO TRUE

      *    EVALUATE TRUE
      *        WHEN ACTIDINI OF COBIL0AI = SPACES OR LOW-VALUES
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Acct ID can NOT be empty...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO ACTIDINL OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *        WHEN OTHER
      *            CONTINUE
      *    END-EVALUATE

      *    IF NOT ERR-FLG-ON
      *        MOVE ACTIDINI  OF COBIL0AI TO ACCT-ID
      *                                      XREF-ACCT-ID

      *        EVALUATE CONFIRMI OF COBIL0AI
      *            WHEN 'Y'
      *            WHEN 'y'
      *                SET CONF-PAY-YES TO TRUE
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=READ-ACCTDAT-FILE'.
      *                PERFORM READ-ACCTDAT-FILE
      *            WHEN 'N'
      *            WHEN 'n'
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=CLEAR-CURRENT-SCREEN'.
      *                PERFORM CLEAR-CURRENT-SCREEN
      *                MOVE 'Y'     TO WS-ERR-FLG
      *            WHEN SPACES
      *            WHEN LOW-VALUES
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=READ-ACCTDAT-FILE'.
      *                PERFORM READ-ACCTDAT-FILE
      *            WHEN OTHER
      *                MOVE 'Y'     TO WS-ERR-FLG
      *                MOVE 'Invalid value. Valid values are (Y/N)...'
      *                             TO WS-MESSAGE
      *                MOVE -1      TO CONFIRML OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=SEND-BILLPAY-SCREEN'.
      *                PERFORM SEND-BILLPAY-SCREEN
      *        END-EVALUATE

      *        MOVE ACCT-CURR-BAL TO WS-CURR-BAL
      *        MOVE WS-CURR-BAL   TO CURBALI    OF COBIL0AI
      *    END-IF

      *    IF NOT ERR-FLG-ON
      *        IF ACCT-CURR-BAL <= ZEROS AND
      *           ACTIDINI OF COBIL0AI NOT = SPACES AND LOW-VALUES
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'You have nothing to pay...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO ACTIDINL OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *        END-IF
      *    END-IF

      *    IF NOT ERR-FLG-ON

      *        IF CONF-PAY-YES
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=READ-CXACAIX-FILE'.
      *            PERFORM READ-CXACAIX-FILE
      *            MOVE HIGH-VALUES TO TRAN-ID
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=STARTBR-TRANSACT-FILE'.
      *            PERFORM STARTBR-TRANSACT-FILE
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=READPREV-TRANSACT-FILE'.
      *            PERFORM READPREV-TRANSACT-FILE
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=ENDBR-TRANSACT-FILE'.
      *            PERFORM ENDBR-TRANSACT-FILE
      *            MOVE TRAN-ID     TO WS-TRAN-ID-NUM
      *            ADD 1 TO WS-TRAN-ID-NUM
      *            INITIALIZE TRAN-RECORD
      *            MOVE WS-TRAN-ID-NUM       TO TRAN-ID
      *            MOVE '02'                 TO TRAN-TYPE-CD
      *            MOVE 2                    TO TRAN-CAT-CD
      *            MOVE 'POS TERM'           TO TRAN-SOURCE
      *            MOVE 'BILL PAYMENT - ONLINE' TO TRAN-DESC
      *            MOVE ACCT-CURR-BAL        TO TRAN-AMT
      *            MOVE XREF-CARD-NUM        TO TRAN-CARD-NUM
      *            MOVE 999999999            TO TRAN-MERCHANT-ID
      *            MOVE 'BILL PAYMENT'       TO TRAN-MERCHANT-NAME
      *            MOVE 'N/A'                TO TRAN-MERCHANT-CITY
      *            MOVE 'N/A'                TO TRAN-MERCHANT-ZIP
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=GET-CURRENT-TIMESTAMP'.
      *            PERFORM GET-CURRENT-TIMESTAMP
      *            MOVE WS-TIMESTAMP         TO TRAN-ORIG-TS
      *                                         TRAN-PROC-TS
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=WRITE-TRANSACT-FILE'.
      *            PERFORM WRITE-TRANSACT-FILE
      *            COMPUTE ACCT-CURR-BAL = ACCT-CURR-BAL - TRAN-AMT
      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=UPDATE-ACCTDAT-FILE'.
      *            PERFORM UPDATE-ACCTDAT-FILE
      *        ELSE
      *            MOVE 'Confirm to make a bill payment...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO CONFIRML OF COBIL0AI
      *        END-IF

      *    DISPLAY 'SPECTER-CALL:FROM=PROCESS-ENTER-KEY:TO=SEND-BILLPAY-SCREEN'.
      *        PERFORM SEND-BILLPAY-SCREEN

      *    END-IF.

      *----------------------------------------------------------------*
      *                      GET-CURRENT-TIMESTAMP
      *----------------------------------------------------------------*
      *GET-CURRENT-TIMESTAMP.
      *    DISPLAY 'SPECTER-TRACE:GET-CURRENT-TIMESTAMP'.

      *    EXEC CICS ASKTIME
      *      ABSTIME(WS-ABS-TIME)
      *    END-EXEC
      *    DISPLAY 'SPECTER-MOCK:CICS'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ

      *    EXEC CICS FORMATTIME
      *      ABSTIME(WS-ABS-TIME)
      *      YYYYMMDD(WS-CUR-DATE-X10)
      *      DATESEP('-')
      *      TIME(WS-CUR-TIME-X08)
      *      TIMESEP(':')
      *    END-EXEC
      *    DISPLAY 'SPECTER-MOCK:CICS'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ

      *    INITIALIZE WS-TIMESTAMP
      *    MOVE WS-CUR-DATE-X10 TO WS-TIMESTAMP(01:10)
      *    MOVE WS-CUR-TIME-X08 TO WS-TIMESTAMP(12:08)
      *    MOVE ZEROS           TO WS-TIMESTAMP-TM-MS6
      *    .


      *----------------------------------------------------------------*
      *                      RETURN-TO-PREV-SCREEN
      *----------------------------------------------------------------*
      *RETURN-TO-PREV-SCREEN.
      *    DISPLAY 'SPECTER-TRACE:RETURN-TO-PREV-SCREEN'.

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
      *    GO TO S-SPECTER-EXIT-PARA. 

      *----------------------------------------------------------------*
      *                      SEND-BILLPAY-SCREEN
      *----------------------------------------------------------------*
      *SEND-BILLPAY-SCREEN.
      *    CONTINUE.

      *    DISPLAY 'SPECTER-CALL:FROM=SEND-BILLPAY-SCREEN:TO=POPULATE-HEADER-INFO'.
      *    PERFORM POPULATE-HEADER-INFO

      *    MOVE WS-MESSAGE TO ERRMSGO OF COBIL0AO

      *    EXEC CICS SEND
      *              MAP('COBIL0A')
      *              MAPSET('COBIL00')
      *              FROM(COBIL0AO)
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
      *                      RECEIVE-BILLPAY-SCREEN
      *----------------------------------------------------------------*
      *RECEIVE-BILLPAY-SCREEN.
      *    DISPLAY 'SPECTER-TRACE:RECEIVE-BILLPAY-SCREEN'.

      *    EXEC CICS RECEIVE
      *              MAP('COBIL0A')
      *              MAPSET('COBIL00')
      *              INTO(COBIL0AI)
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

      *----------------------------------------------------------------*
      *                      POPULATE-HEADER-INFO
      *----------------------------------------------------------------*
      *POPULATE-HEADER-INFO.
      *    DISPLAY 'SPECTER-TRACE:POPULATE-HEADER-INFO'.

      *    MOVE FUNCTION CURRENT-DATE  TO WS-CURDATE-DATA

      *    MOVE CCDA-TITLE01           TO TITLE01O OF COBIL0AO
      *    MOVE CCDA-TITLE02           TO TITLE02O OF COBIL0AO
      *    MOVE WS-TRANID              TO TRNNAMEO OF COBIL0AO
      *    MOVE WS-PGMNAME             TO PGMNAMEO OF COBIL0AO

      *    MOVE WS-CURDATE-MONTH       TO WS-CURDATE-MM
      *    MOVE WS-CURDATE-DAY         TO WS-CURDATE-DD
      *    MOVE WS-CURDATE-YEAR(3:2)   TO WS-CURDATE-YY

      *    MOVE WS-CURDATE-MM-DD-YY    TO CURDATEO OF COBIL0AO

      *    MOVE WS-CURTIME-HOURS       TO WS-CURTIME-HH
      *    MOVE WS-CURTIME-MINUTE      TO WS-CURTIME-MM
      *    MOVE WS-CURTIME-SECOND      TO WS-CURTIME-SS

      *    MOVE WS-CURTIME-HH-MM-SS    TO CURTIMEO OF COBIL0AO.

      *----------------------------------------------------------------*
      *                      READ-ACCTDAT-FILE
      *----------------------------------------------------------------*
      *READ-ACCTDAT-FILE.
      *    CONTINUE.

      *    EXEC CICS READ
      *         DATASET   (WS-ACCTDAT-FILE)
      *         INTO      (ACCOUNT-RECORD)
      *         LENGTH    (LENGTH OF ACCOUNT-RECORD)
      *         RIDFLD    (ACCT-ID)
      *         KEYLENGTH (LENGTH OF ACCT-ID)
      *         UPDATE
      *         RESP      (WS-RESP-CD)
      *         RESP2     (WS-REAS-CD)
      *    END-EXEC
      *    DISPLAY 'SPECTER-MOCK:CICS-READ'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ
      *    MOVE MOCK-NUM-STATUS TO WS-RESP-CD
      *    MOVE 0 TO WS-REAS-CD

      *    EVALUATE WS-RESP-CD
      *        WHEN 0
      *            CONTINUE
      *        WHEN 13
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Account ID NOT found...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO ACTIDINL OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=READ-ACCTDAT-FILE:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *        WHEN OTHER
      *            DISPLAY 'RESP:' WS-RESP-CD 'REAS:' WS-REAS-CD
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Unable to lookup Account...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO ACTIDINL OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=READ-ACCTDAT-FILE:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *    END-EVALUATE.

      *----------------------------------------------------------------*
      *                      UPDATE-ACCTDAT-FILE
      *----------------------------------------------------------------*
      *UPDATE-ACCTDAT-FILE.
      *    CONTINUE.

      *    EXEC CICS REWRITE
      *         DATASET   (WS-ACCTDAT-FILE)
      *         FROM      (ACCOUNT-RECORD)
      *         LENGTH    (LENGTH OF ACCOUNT-RECORD)
      *         RESP      (WS-RESP-CD)
      *         RESP2     (WS-REAS-CD)
      *    END-EXEC
      *    DISPLAY 'SPECTER-MOCK:CICS'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ
      *    MOVE MOCK-NUM-STATUS TO WS-RESP-CD
      *    MOVE 0 TO WS-REAS-CD

      *    EVALUATE WS-RESP-CD
      *        WHEN 0
      *            CONTINUE
      *        WHEN 13
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Account ID NOT found...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO ACTIDINL OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=UPDATE-ACCTDAT-FILE:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *        WHEN OTHER
      *            DISPLAY 'RESP:' WS-RESP-CD 'REAS:' WS-REAS-CD
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Unable to Update Account...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO ACTIDINL OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=UPDATE-ACCTDAT-FILE:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *    END-EVALUATE.

      *----------------------------------------------------------------*
      *                      READ-CXACAIX-FILE
      *----------------------------------------------------------------*
      *READ-CXACAIX-FILE.
      *    CONTINUE.

      *    EXEC CICS READ
      *         DATASET   (WS-CXACAIX-FILE)
      *         INTO      (CARD-XREF-RECORD)
      *         LENGTH    (LENGTH OF CARD-XREF-RECORD)
      *         RIDFLD    (XREF-ACCT-ID)
      *         KEYLENGTH (LENGTH OF XREF-ACCT-ID)
      *         RESP      (WS-RESP-CD)
      *         RESP2     (WS-REAS-CD)
      *    END-EXEC
      *    DISPLAY 'SPECTER-MOCK:CICS-READ'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ
      *    MOVE MOCK-NUM-STATUS TO WS-RESP-CD
      *    MOVE 0 TO WS-REAS-CD

      *    EVALUATE WS-RESP-CD
      *        WHEN 0
      *            CONTINUE
      *        WHEN 13
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Account ID NOT found...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO ACTIDINL OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=READ-CXACAIX-FILE:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *        WHEN OTHER
      *            DISPLAY 'RESP:' WS-RESP-CD 'REAS:' WS-REAS-CD
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Unable to lookup XREF AIX file...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO ACTIDINL OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=READ-CXACAIX-FILE:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *    END-EVALUATE.

      *----------------------------------------------------------------*
      *                      STARTBR-TRANSACT-FILE
      *----------------------------------------------------------------*
      *STARTBR-TRANSACT-FILE.
      *    CONTINUE.

      *    EXEC CICS STARTBR
      *         DATASET   (WS-TRANSACT-FILE)
      *         RIDFLD    (TRAN-ID)
      *         KEYLENGTH (LENGTH OF TRAN-ID)
      *         RESP      (WS-RESP-CD)
      *         RESP2     (WS-REAS-CD)
      *    END-EXEC
      *    DISPLAY 'SPECTER-MOCK:CICS-STARTBR'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ
      *    MOVE MOCK-NUM-STATUS TO WS-RESP-CD
      *    MOVE 0 TO WS-REAS-CD

      *    EVALUATE WS-RESP-CD
      *        WHEN 0
      *            CONTINUE
      *        WHEN 13
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Transaction ID NOT found...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO ACTIDINL OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=STARTBR-TRANSACT-FILE:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *        WHEN OTHER
      *            DISPLAY 'RESP:' WS-RESP-CD 'REAS:' WS-REAS-CD
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Unable to lookup Transaction...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO ACTIDINL OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=STARTBR-TRANSACT-FILE:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *    END-EVALUATE.

      *----------------------------------------------------------------*
      *                      READPREV-TRANSACT-FILE
      *----------------------------------------------------------------*
      *READPREV-TRANSACT-FILE.
      *    CONTINUE.

      *    EXEC CICS READPREV
      *         DATASET   (WS-TRANSACT-FILE)
      *         INTO      (TRAN-RECORD)
      *         LENGTH    (LENGTH OF TRAN-RECORD)
      *         RIDFLD    (TRAN-ID)
      *         KEYLENGTH (LENGTH OF TRAN-ID)
      *         RESP      (WS-RESP-CD)
      *         RESP2     (WS-REAS-CD)
      *    END-EXEC
      *    DISPLAY 'SPECTER-MOCK:CICS-READPREV'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ
      *    MOVE MOCK-NUM-STATUS TO WS-RESP-CD
      *    MOVE 0 TO WS-REAS-CD

      *    EVALUATE WS-RESP-CD
      *        WHEN 0
      *            CONTINUE
      *        WHEN 20
      *            MOVE ZEROS TO TRAN-ID
      *        WHEN OTHER
      *            DISPLAY 'RESP:' WS-RESP-CD 'REAS:' WS-REAS-CD
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Unable to lookup Transaction...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO ACTIDINL OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=READPREV-TRANSACT-FILE:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *    END-EVALUATE.

      *----------------------------------------------------------------*
      *                      ENDBR-TRANSACT-FILE
      *----------------------------------------------------------------*
      *ENDBR-TRANSACT-FILE.
      *    CONTINUE.

      *    EXEC CICS ENDBR
      *         DATASET   (WS-TRANSACT-FILE)
      *    END-EXEC.
      *    DISPLAY 'SPECTER-MOCK:CICS-ENDBR'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ.

      *----------------------------------------------------------------*
      *                      WRITE-TRANSACT-FILE
      *----------------------------------------------------------------*
      *WRITE-TRANSACT-FILE.
      *    CONTINUE.

      *    EXEC CICS WRITE
      *         DATASET   (WS-TRANSACT-FILE)
      *         FROM      (TRAN-RECORD)
      *         LENGTH    (LENGTH OF TRAN-RECORD)
      *         RIDFLD    (TRAN-ID)
      *         KEYLENGTH (LENGTH OF TRAN-ID)
      *         RESP      (WS-RESP-CD)
      *         RESP2     (WS-REAS-CD)
      *    END-EXEC
      *    DISPLAY 'SPECTER-MOCK:CICS-WRITE'
      *    READ MOCK-FILE INTO MOCK-RECORD
      *       AT END
      *         MOVE '00' TO MOCK-ALPHA-STATUS
      *         MOVE 0 TO MOCK-NUM-STATUS
      *    END-READ
      *    MOVE MOCK-NUM-STATUS TO WS-RESP-CD
      *    MOVE 0 TO WS-REAS-CD

      *    EVALUATE WS-RESP-CD
      *        WHEN 0
      *    DISPLAY 'SPECTER-CALL:FROM=WRITE-TRANSACT-FILE:TO=INITIALIZE-ALL-FIELDS'.
      *            PERFORM INITIALIZE-ALL-FIELDS
      *            MOVE SPACES             TO WS-MESSAGE
      *            MOVE DFHGREEN           TO ERRMSGC  OF COBIL0AO
      *            STRING 'Payment successful. '     DELIMITED BY SIZE
      *              ' Your Transaction ID is ' DELIMITED BY SIZE
      *                   TRAN-ID  DELIMITED BY SPACE
      *                   '.' DELIMITED BY SIZE
      *              INTO WS-MESSAGE
      *    DISPLAY 'SPECTER-CALL:FROM=WRITE-TRANSACT-FILE:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *        WHEN 15
      *        WHEN 14
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Tran ID already exist...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO ACTIDINL OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=WRITE-TRANSACT-FILE:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *        WHEN OTHER
      *            DISPLAY 'RESP:' WS-RESP-CD 'REAS:' WS-REAS-CD
      *            MOVE 'Y'     TO WS-ERR-FLG
      *            MOVE 'Unable to Add Bill pay Transaction...' TO
      *                            WS-MESSAGE
      *            MOVE -1       TO ACTIDINL OF COBIL0AI
      *    DISPLAY 'SPECTER-CALL:FROM=WRITE-TRANSACT-FILE:TO=SEND-BILLPAY-SCREEN'.
      *            PERFORM SEND-BILLPAY-SCREEN
      *    END-EVALUATE.

      *----------------------------------------------------------------*
      *                      CLEAR-CURRENT-SCREEN
      *----------------------------------------------------------------*
      *CLEAR-CURRENT-SCREEN.
      *    CONTINUE.

      *    DISPLAY 'SPECTER-CALL:FROM=CLEAR-CURRENT-SCREEN:TO=INITIALIZE-ALL-FIELDS'.
      *    PERFORM INITIALIZE-ALL-FIELDS
      *    DISPLAY 'SPECTER-CALL:FROM=CLEAR-CURRENT-SCREEN:TO=SEND-BILLPAY-SCREEN'.
      *    PERFORM SEND-BILLPAY-SCREEN.

      *----------------------------------------------------------------*
      *                      INITIALIZE-ALL-FIELDS
      *----------------------------------------------------------------*
      *INITIALIZE-ALL-FIELDS.
      *    DISPLAY 'SPECTER-TRACE:INITIALIZE-ALL-FIELDS'.

      *    MOVE -1              TO ACTIDINL OF COBIL0AI
      *    MOVE SPACES          TO ACTIDINI OF COBIL0AI
      *                            CURBALI  OF COBIL0AI
      *                            CONFIRMI OF COBIL0AI
      *                            WS-MESSAGE.



      *
      * Ver: CardDemo_v1.0-15-g27d6c6f-68 Date: 2022-07-19 23:12:32 CDT
      *

      * SPECTER: exit paragraph for CICS RETURN/XCTL
      *S-SPECTER-EXIT-PARA. 
      *    CONTINUE.
      *    STOP RUN.
