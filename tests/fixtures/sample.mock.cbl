       IDENTIFICATION DIVISION.
       PROGRAM-ID. TESTPROG.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-STATUS    PIC X(2).
       01 WS-FLAG      PIC X(1).
       01 WS-AMOUNT    PIC 9(9).
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
           MOVE '00' TO WS-STATUS
           IF WS-FLAG = 'Y'
               DISPLAY "@@B:2:T"
           ELSE
               DISPLAY "@@B:2:F"
           END-IF.
       3000-PROCESS.
           DISPLAY "SPECTER-TRACE:3000-PROCESS"
           DISPLAY "SPECTER-CALL:FROM=1000-MAIN:TO=3000-PROCESS"
           ADD 1 TO WS-AMOUNT.
       9000-ERROR.
           DISPLAY "SPECTER-TRACE:9000-ERROR"
           DISPLAY "SPECTER-MOCK:WRITE-ERROR-LOG".
