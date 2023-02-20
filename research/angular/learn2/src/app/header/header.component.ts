import { Component } from '@angular/core';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.css']
})

export class HeaderComponent {

  slogan: string = 'shop the stop';

  source: string = '/assets/shopping.png';

  // or you can use a function, or is this a method
  getslogan() {
    return "new shop the stop";
  }


}
