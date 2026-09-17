Imports System
Imports System.Collections.Generic

' Optional companion example. NOT executed by Odoo.
Public Class CarWashVehicle
    Public Property Plate As String
    Public Property ServiceName As String
    Public Property StationName As String
    Public Property Progress As Integer
End Class

Module CarWashKioskPreview
    Sub Main()
        Dim cars As New List(Of CarWashVehicle) From {
            New CarWashVehicle With {
                .Plate = "9087867",
                .ServiceName = "Car Wash",
                .StationName = "A0",
                .Progress = 65
            }
        }

        Console.WriteLine("Crystal Clean - External Kiosk Preview")
        For Each car In cars
            Console.WriteLine($"{car.Plate} | {car.ServiceName} | {car.StationName} | {car.Progress}%")
        Next
    End Sub
End Module
