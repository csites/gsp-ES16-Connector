# gsp-ES16-Connector
GSPro OpenAPI to Ernest Sports ES16 Tour Plus Connector

This is a connector application that connects to the GSPro Golf Simulator's OpenAPI interface and Ernest Sport's ES16, ES Tour Plus (V1.0 and V2.0), and the ES2020 Launch Monitors.   It's written in Python for easy portability and is open source.   The ES16 communicates via a Bluetooth connection which emulates a serial line connection and on Windows shows up as COM7.  For each swing, it sends to 168-byte strings that contain all of the ball and club data of the swing.  This is then reformated into the JSON structure used by the OpenAPI connector of GSPro.   The connector looks for changes in the Club selection and sends those to the ES16.   The GSP always lets the connector know the distance to the hole so on approach to a green if the ball is within 40 yards, it will send a special club selection called 'CHP' which enables a camera-only mode.  

The ES16 uses dual optical and quad aperture Doppler radar and does the following; radar is responsible for Ball Speed and Club Speed.  The optical systems are responsible for Club face angle, club path, ball spin, side spin, launch angle, etc.  The ES2020 is purely an optical system.

Acknowlegements:  This program borrows heavily from rowengb/GSPro-MLM2PRO-OCR-Connector project.  Mainly it serves as a guide to build the interface between a stock set of LM measurements and the GSPro OpenAPI.  Because the Ernest Sports Tour Plus and friends have putting built-in, the putting code has been removed as well as well. 
