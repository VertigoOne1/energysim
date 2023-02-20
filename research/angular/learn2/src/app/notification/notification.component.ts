import { Component } from '@angular/core';

@Component({
  selector: 'app-notification',
  template: `<div class="alert alert-success" [ngClass]="{fadeOut: displayNotification}">
              <p>
                Using template property instead of templateurl path to html file
              </p>
              <p class=styles>
              Using styles in line instead of css file
            </p>
            <p class=styles>
            using bootstrap as well in the div
            </p>
            <div class="close"><button class="btn" (click)="hideNotification()">X</button></div>
             </div>`,
  styles: [
    '.noti{background-color: pink;}',
    '.styles{background-color:orange;}',
    '.fadeOut{visibility: hidden; opacity: 0;transition: visibility 0s 1s, opacity 1s linear;}'
  ]
})

// @Component({
//   selector: 'app-notification',
//   template: `<div class="alert alert-success" [hidden]="displayNotification">
//               <p>
//                 Using template property instead of templateurl path to html file
//               </p>
//               <p class=styles>
//               Using styles in line instead of css file
//             </p>
//             <p class=styles>
//             using bootstrap as well in the div
//             </p>
//             <div class="close"><button class="btn" (click)="hideNotification()">X</button></div>
//              </div>`,
//   styles: ['.noti{background-color: pink;}','.styles{background-color:orange;}']
// })

export class NotificationComponent {

  displayNotification: boolean = false

  hideNotification() {

    this.displayNotification = true

  }

}
