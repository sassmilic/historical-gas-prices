//SPDX-License-Identifier: Unlicense
pragma solidity ^0.6.12;

contract MockContract {
  uint256 data;

  function updateData(uint256 updatedData) external {
    data = updatedData;
  }
}
