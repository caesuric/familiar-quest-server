@echo off
for /f %%G in ('dir /b proto\*.proto') do \Python36\python -m grpc_tools.protoc --python_out=. --grpc_python_out=. -Iproto %%G
for /f %%G in ('dir /b proto\*.proto') do ..\FamiliarQuestMainGame\Packages\Grpc.Tools.1.20.1\tools\windows_x86\protoc.exe --csharp_out=..\FamiliarQuestMainGame\Assets\Scripts\Proto --grpc_out=..\FamiliarQuestMainGame\Assets\Scripts\Proto --plugin=protoc-gen-grpc=..\FamiliarQuestMainGame\Packages\Grpc.Tools.1.20.1\tools\windows_x86\grpc_csharp_plugin.exe -Iproto %%G
