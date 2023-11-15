# gsp-ES16-Connector
GSPro OpenAPI to Ernest Sports ES16 Tour Plus Connector

This is a connector application that connects to the GSPro Golf Simulator's OpenAPI interface and Ernest Sport's ES16, ES Tour Plus (V1.0 and V2.0), and the ES2020 Launch Monitors.   It's written in Python for easy portability and is open source.   The ES16 communicates via a Bluetooth connection which emulates a serial line connection and on Windows shows up as COM7.  For each swing, it sends to 168-byte strings that contain all of the ball and club data of the swing.  This is then reformated into the JSON structure used by the OpenAPI connector of GSPro.   The connector looks for changes in the Club selection and sends those to the ES16.   The GSP always lets the connector know the distance to the hole so on approach to a green if the ball is within 40 yards, it will send a special club selection called 'CHP' which enables a camera-only mode.  

The ES16 uses dual optical and quad aperture Doppler radar and does the following; radar is responsible for Ball Speed and Club Speed.  The optical systems are responsible for Club face angle, club path, ball spin, side spin, launch angle, etc.  The ES2020 is purely an optical system.

ES16parser9.py is the 9th makeover of a parser I originally wrote with the Linux 'sed' command.  Basically, it is the tool I've used to build
proof of concepts for reading the serial activity of the ES16 (and friends) and parsing the data streams live.  It demonstrated one aspect I never knew of; that being the issue with "fat" shots.  On "fat" shots the ES16 returns only raw Radar data which consists of Ball Speed and Club Speed in a single string that begins with ESTP, which consists of 26 characters of data padded with zeros to up the then word 'End" with a final length = 168.   An Example would be: 
ESTPPrt001CS054.0BS000.0CL4Hy000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000End
On full swings, we are given both sets of data.  In other words, two lines of data.  The first line is exactly as above; giving just the radar data.   The second line of 168 characters looks like:
ES16Prt001CS067.0BS082.8CD000.0TD000.0LA12.8SP02259SF1.23CL4HySPA-10.3DIR-06.2LDA00.0AA-2.6DL17.0MH000.0SC+000.0ST+000.0CPTH-03.3CFAC-07.0SPL19.6HT00.00BV8.37VER179End
Which contains all of the optically read data from the ES16 with the minor caveat being the CS and BS are radar (not optical).  The ES2020 returns a similar string but it begins with ES20 and likely fills out all values.  This is what I parse.   

Acknowlegements:  This program borrows heavily from rowengb/GSPro-MLM2PRO-OCR-Connector project.  Mainly it serves as a guide to build the interface between a stock set of LM measurements and the GSPro OpenAPI.  Because the Ernest Sports Tour Plus and friends have putting built-in, the putting code has been removed as well as well. 
