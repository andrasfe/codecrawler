       IDENTIFICATION DIVISION.
       PROGRAM-ID. TESTPROG.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT MOCK-FILE ASSIGN TO
              'MOCKDATA'
              ORGANIZATION IS LINE SEQUENTIAL
              FILE STATUS IS MOCK-FILE-STATUS.
       DATA DIVISION.
       FILE SECTION.
       FD MOCK-FILE.
       01 MOCK-FILE-RECORD     PIC X(80).
       WORKING-STORAGE SECTION.
      * SPECTER MOCK INFRASTRUCTURE
       01 MOCK-RECORD.
           05 MOCK-OP-KEY        PIC X(30).
           05 MOCK-ALPHA-STATUS  PIC X(20).
           05 MOCK-NUM-STATUS    PIC S9(09).
           05 MOCK-FILLER        PIC X(21).
       01 MOCK-FILE-STATUS      PIC XX VALUE '00'.
      * APPLICATION FIELDS
       01 WS-STATUS             PIC X(02).
           88 STATUS-OK         VALUE '00'.
           88 STATUS-ERROR      VALUE '99'.
           88 STATUS-WARNING    VALUE '04'.
       01 WS-FLAG               PIC X(01) VALUE 'N'.
           88 FLAG-YES          VALUE 'Y'.
           88 FLAG-NO           VALUE 'N'.
       01 WS-AMOUNT             PIC S9(07)V99 COMP-3.
       01 WS-ACCOUNT-ID         PIC 9(11).
       01 WS-CUSTOMER-NAME      PIC X(30) VALUE SPACES.
       01 WS-TRANSACTION-DT     PIC 9(08).
       01 WS-PROCESS-TIME       PIC 9(06).
       01 WS-RECORD-CNT         PIC 9(05) VALUE ZERO.
       01 WS-ERROR-FLG          PIC X(01) VALUE 'N'.
       01 WS-FILE-STATUS        PIC X(02).
       01 SQLCODE               PIC S9(09) COMP VALUE 0.
       01 WS-VARIABLES.
           05 WS-SUB-AMOUNT     PIC S9(05)V99.
           05 WS-CODE           PIC X(04).
           05 FILLER            PIC X(10).
       01 WS-REDEF-GROUP.
           05 WS-REDEF-ALPHA    PIC X(09).
           05 WS-REDEF-NUM REDEFINES
              WS-REDEF-ALPHA    PIC 9(09).
       PROCEDURE DIVISION.
       1000-MAIN.
           DISPLAY "SPECTER-TRACE:1000-MAIN"
           PERFORM 2000-VALIDATE
           IF WS-STATUS = '00'
               DISPLAY "@@B:1:T"
               PERFORM 3000-PROCESS
           ELSE
               DISPLAY "@@B:1:F"
               PERFORM 9000-ERROR
           END-IF
           STOP RUN.
       2000-VALIDATE.
           DISPLAY "SPECTER-TRACE:2000-VALIDATE"
           DISPLAY 'SPECTER-MOCK:READ-ACCOUNT'
           READ MOCK-FILE INTO MOCK-RECORD
              AT END
                MOVE '  ' TO MOCK-ALPHA-STATUS
                MOVE 0 TO MOCK-NUM-STATUS
           END-READ
           MOVE MOCK-ALPHA-STATUS TO WS-STATUS
           IF WS-FLAG = 'Y'
               DISPLAY "@@B:2:T"
           ELSE
               DISPLAY "@@B:2:F"
           END-IF
           IF WS-AMOUNT > 1000
               CONTINUE
           END-IF
           EVALUATE WS-STATUS
               WHEN '00'
                   CONTINUE
               WHEN '04'
                   CONTINUE
               WHEN '99'
                   CONTINUE
               WHEN OTHER
                   CONTINUE
           END-EVALUATE.
       3000-PROCESS.
           DISPLAY "SPECTER-TRACE:3000-PROCESS"
           DISPLAY "SPECTER-CALL:FROM=1000-MAIN:TO=3000-PROCESS"
           ADD 1 TO WS-AMOUNT.
       9000-ERROR.
           DISPLAY "SPECTER-TRACE:9000-ERROR"
           DISPLAY "SPECTER-MOCK:WRITE-ERROR-LOG".
