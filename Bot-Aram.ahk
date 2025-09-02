#Include <Simulator>

/*
-------------------------------
          Functions
-------------------------------
*/

RunGame() {
    ;INIT
	Sim := Simulator()
    static loaded := false
	SELECT_ALLY_ARR := [Sim.SELECT_ALLY_1, Sim.SELECT_ALLY_2, Sim.SELECT_ALLY_3, Sim.SELECT_ALLY_4]
    ACTIVE_RANGE := 500
	static AllyCurrent := 0
	
    ;START GAME LOOP
    loop {

	if (!WinActive(Sim.GAME_PROCESS)) { ; GAME DOWN
		; LOOK FOR GAME
		if(WinExist(Sim.CLIENT_PROCESS))
			WinActivate(Sim.CLIENT_PROCESS)
		if (WinActive(Sim.CLIENT_PROCESS)) { ; CLIENT ACTIVE
			Sim.RunClient(Sim.CHAMPION)
			continue
		} else {
			while (!WinActive(Sim.GAME_PROCESS) && !WinActive(Sim.CLIENT_PROCESS)) { ; Transition phase
				if(WinExist(Sim.GAME_PROCESS)) ; ACTIVATE GAME
					WinActivate(Sim.GAME_PROCESS)
				Sleep(1000)
			}
		}
	}

	;Shop phase
	if (Sim.ImageFinder.IsDead()) {
		Sim.BuyRecommended()
		loop 3 {
			Sim.LevelUp() 
		}
		Sim.Surrender()
	}
	
	; Combat
	AllyPosXY := Sim.ImageFinder.FindAllyXY()
	if (AllyPosXY) { ; ally found
		if (EnemyPosXY := Sim.ImageFinder.FindEnemyXY()) { 
			;move toward enemy if seen
			Click(EnemyPosXY[1], EnemyPosXY[2], "R")
			Send("{" Sim.CENTER_CAMERA " down}")
			if (EnemyPosXY := Sim.ImageFinder.FindEnemyXY()) {
				EnemyDistance := Sim.GetDistance(Sim.SCREEN_CENTER, EnemyPosXY)
				if (EnemyDistance < ACTIVE_RANGE) {
					Sim.AttackEnemy(&EnemyPosXY)
				}
			}
			Sleep 400
			Send("{" Sim.CENTER_CAMERA " up}")
		} 
	} else { ; look for ally
		num := Random(1, 4)
		AllyCurrent := SELECT_ALLY_ARR[num]
		Sleep(300)
	}
	Sim.FollowAlly(AllyCurrent, 250)
	Sleep 200

    } ;END LOOP
}

RunTest() {

}

/*
-------------------------------
          Execution
-------------------------------
*/

;Run script
Home::
{
RunGame()
return
} 

;Run script tests
Ins::
{ 
RunTest()
return
} 

;Stop script
Del::ExitApp()
End::Reload()

