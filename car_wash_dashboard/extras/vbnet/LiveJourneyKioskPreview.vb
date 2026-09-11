Imports System

' Crystal Clean V4 - optional desktop/kiosk reference.
' NOT loaded by Odoo. Odoo runtime remains Python + OWL + QWeb + CSS.
Module LiveJourneyKioskPreview
    Private Function SmoothStep(t As Double) As Double
        t = Math.Max(0.0, Math.Min(1.0, t))
        Return t * t * (3.0 - 2.0 * t)
    End Function

    Private Function JourneyPosition(fromPct As Double, toPct As Double, frame01 As Double) As Double
        Return fromPct + (toPct - fromPct) * SmoothStep(frame01)
    End Function

    Sub Main()
        For i As Integer = 0 To 10
            Console.WriteLine(JourneyPosition(25, 50, i / 10.0).ToString("F2") & "%")
        Next
    End Sub
End Module
